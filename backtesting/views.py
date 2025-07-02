from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Count, Avg, Sum
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.urls import reverse
from django import forms
import json
from datetime import datetime, timedelta
import logging
from .models import TradingStrategy, BacktestResult, Trade, Symbol, TechnicalIndicator, StrategyRule
from .forms import StrategyForm, BacktestForm, QuickStrategyForm
from .utils import run_strategy_backtest

logger = logging.getLogger(__name__)


@login_required
def strategy_list(request):
    """List all strategies for the current user"""
    strategies = TradingStrategy.objects.filter(created_by=request.user)
    
    # Calculate statistics
    total_strategies = strategies.count()
    active_strategies = strategies.filter(is_active=True).count()
    
    # Performance statistics
    completed_backtests = BacktestResult.objects.filter(
        strategy__created_by=request.user, 
        status='completed'
    )
    avg_performance = completed_backtests.aggregate(Avg('total_return'))['total_return__avg'] or 0
    best_backtest = completed_backtests.order_by('-total_return').first()
    best_strategy_return = best_backtest.total_return if best_backtest else 0
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        strategies = strategies.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
    
    # Filter by strategy type
    strategy_type = request.GET.get('type', '')
    if strategy_type:
        strategies = strategies.filter(strategy_type=strategy_type)
    
    paginator = Paginator(strategies, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'strategies': page_obj,
        'total_strategies': total_strategies,
        'active_strategies': active_strategies,
        'avg_performance': avg_performance * 100,  # Convert to percentage
        'best_strategy_return': best_strategy_return * 100,  # Convert to percentage
        'search_query': search_query,
        'strategy_type': strategy_type,
        'strategy_types': TradingStrategy.STRATEGY_TYPES,
    }
    return render(request, 'backtesting/strategy_list.html', context)


@login_required
def strategy_create(request):
    """Create a new trading strategy"""
    # Initialize forms for both GET and POST requests
    form = StrategyForm()
    quick_form = QuickStrategyForm()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'advanced')
        
        if form_type == 'quick':
            quick_form = QuickStrategyForm(request.POST)
            if quick_form.is_valid():
                try:
                    strategy = quick_form.create_strategy_from_template(request.user)
                    messages.success(request, f'Strategy "{strategy.name}" created successfully from template!')
                    return redirect('backtesting:strategy_detail', strategy.id)
                except ValidationError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    logger.error(f"Error creating strategy from template: {e}")
                    messages.error(request, f'Error creating strategy: {str(e)}')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = StrategyForm(request.POST)
            if form.is_valid():
                try:
                    strategy = form.save(commit=False)
                    strategy.created_by = request.user
                    strategy.save()
                    form.save_m2m()
                    messages.success(request, f'Strategy "{strategy.name}" created successfully!')
                    return redirect('backtesting:strategy_detail', strategy.id)
                except Exception as e:
                    logger.error(f"Error creating strategy: {e}")
                    messages.error(request, 'Error creating strategy. Please try again.')
            else:
                messages.error(request, 'Please correct the errors below.')
    
    # Get available symbols and indicators
    symbols = Symbol.objects.filter(is_active=True)
    indicators = TechnicalIndicator.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'quick_form': quick_form,
        'symbols': symbols,
        'indicators': indicators,
    }
    return render(request, 'backtesting/strategy_create.html', context)


@login_required
def strategy_detail(request, strategy_id):
    """Display strategy details and related backtests"""
    strategy = get_object_or_404(TradingStrategy, id=strategy_id, created_by=request.user)
    backtests = strategy.backtests.all()[:10]  # Latest 10 backtests
    
    # Calculate strategy statistics
    total_backtests = strategy.backtests.count()
    successful_backtests = strategy.backtests.filter(status='completed').count()
    avg_return = strategy.backtests.filter(status='completed').aggregate(Avg('total_return'))['total_return__avg'] or 0
    
    # Get strategy rules
    buy_rules = strategy.get_buy_rules_list()
    sell_rules = strategy.get_sell_rules_list()
    
    context = {
        'strategy': strategy,
        'backtests': backtests,
        'total_backtests': total_backtests,
        'successful_backtests': successful_backtests,
        'avg_return': avg_return * 100,  # Convert to percentage
        'buy_rules': buy_rules,
        'sell_rules': sell_rules,
        'indicator_config': strategy.get_indicator_config(),
    }
    return render(request, 'backtesting/strategy_detail.html', context)


@login_required
def backtest_create(request, strategy_id=None):
    """Create a new backtest with HTMX support"""
    strategy = None
    if strategy_id:
        strategy = get_object_or_404(TradingStrategy, id=strategy_id, created_by=request.user)
    
    if request.method == 'POST':
        logger.info(f"POST request received. HTMX: {bool(request.headers.get('HX-Request'))}")
        logger.info(f"POST data: {dict(request.POST)}")
        form = BacktestForm(request.POST)
        if form.is_valid():
            try:
                backtest = form.save(commit=False)
                backtest.created_by = request.user
                if strategy:
                    backtest.strategy = strategy
                else:
                    # Filter strategies for current user
                    user_strategies = TradingStrategy.objects.filter(created_by=request.user, is_active=True)
                    if backtest.strategy not in user_strategies:
                        if request.headers.get('HX-Request'):
                            return JsonResponse({
                                'error': 'You can only create backtests for your own strategies.'
                            }, status=400)
                        messages.error(request, 'You can only create backtests for your own strategies.')
                        return redirect('backtesting:backtest_create')
                
                # Validate date range
                if backtest.start_date >= backtest.end_date:
                    if request.headers.get('HX-Request'):
                        return JsonResponse({
                            'error': 'Start date must be before end date.'
                        }, status=400)
                    messages.error(request, 'Start date must be before end date.')
                    return render(request, 'backtesting/backtest_create.html', {
                        'form': form,
                        'strategy': strategy,
                        'strategies': TradingStrategy.objects.filter(created_by=request.user, is_active=True),
                        'selected_strategy_id': strategy.id if strategy else None,
                    })
                
                # Validate strategy has rules and symbols
                if not backtest.strategy.symbols.exists():
                    error_msg = 'The selected strategy has no symbols. Please add symbols to the strategy first.'
                    if request.headers.get('HX-Request'):
                        return JsonResponse({'error': error_msg}, status=400)
                    messages.error(request, error_msg)
                    return redirect('backtesting:strategy_detail', backtest.strategy.id)
                
                if not backtest.strategy.get_buy_rules_list().exists() and not backtest.strategy.get_sell_rules_list().exists():
                    error_msg = 'The selected strategy has no trading rules. Please add rules to the strategy first.'
                    if request.headers.get('HX-Request'):
                        return JsonResponse({'error': error_msg}, status=400)
                    messages.error(request, error_msg)
                    return redirect('backtesting:strategy_detail', backtest.strategy.id)
                
                backtest.save()
                
                # For HTMX requests, return success response and start backtest in background
                if request.headers.get('HX-Request'):
                    try:
                        # Start the backtest process
                        run_strategy_backtest(backtest.id)
                        return JsonResponse({
                            'success': True,
                            'backtest_id': backtest.id,
                            'message': 'Backtest started successfully!',
                            'redirect_url': reverse('backtesting:backtest_detail', kwargs={'backtest_id': backtest.id})
                        })
                    except Exception as e:
                        logger.error(f"Error starting backtest: {e}")
                        backtest.delete()
                        return JsonResponse({
                            'error': f'Error starting backtest: {str(e)}'
                        }, status=500)
                
                # For regular requests, start backtest and redirect
                try:
                    run_strategy_backtest(backtest.id)
                    messages.success(request, 'Backtest started successfully!')
                    return redirect('backtesting:backtest_detail', backtest.id)
                except Exception as e:
                    logger.error(f"Error starting backtest: {e}")
                    messages.error(request, f'Error starting backtest: {str(e)}')
                    backtest.delete()
                    
            except Exception as e:
                logger.error(f"Error creating backtest: {e}")
                if request.headers.get('HX-Request'):
                    return JsonResponse({
                        'error': f'Error creating backtest: {str(e)}'
                    }, status=500)
                messages.error(request, f'Error creating backtest: {str(e)}')
        else:
            # Form validation errors
            logger.error(f"Form validation errors: {form.errors}")
            if request.headers.get('HX-Request'):
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                error_message = 'Please correct the following errors: ' + '; '.join(errors)
                logger.error(f"Returning HTMX error: {error_message}")
                return JsonResponse({
                    'error': error_message
                }, status=400)
            else:
                messages.error(request, 'Please correct the form errors.')
    else:
        form = BacktestForm()
        if strategy:
            form.initial['strategy'] = strategy
        
        # Filter strategies for current user
        form.fields['strategy'].queryset = TradingStrategy.objects.filter(
            created_by=request.user, is_active=True
        )
    
    # Get all strategies for the template
    strategies = TradingStrategy.objects.filter(created_by=request.user, is_active=True)
    
    context = {
        'form': form,
        'strategy': strategy,
        'strategies': strategies,
        'selected_strategy_id': strategy.id if strategy else None,
    }
    return render(request, 'backtesting/backtest_create.html', context)


@login_required
def backtest_list(request):
    """List all backtests for the current user"""
    all_backtests = BacktestResult.objects.filter(created_by=request.user)
    
    # Calculate statistics
    total_backtests = all_backtests.count()
    completed_backtests = all_backtests.filter(status='completed').count()
    running_backtests = all_backtests.filter(status='running').count()
    avg_return = all_backtests.filter(status='completed').aggregate(Avg('total_return'))['total_return__avg'] or 0
    
    backtests = all_backtests
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        backtests = backtests.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        backtests = backtests.filter(
            Q(name__icontains=search_query) | Q(strategy__name__icontains=search_query)
        )
    
    paginator = Paginator(backtests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'backtest_list': page_obj,
        'total_backtests': total_backtests,
        'completed_backtests': completed_backtests,
        'running_backtests': running_backtests,
        'avg_return': avg_return * 100,  # Convert to percentage
        'search_query': search_query,
        'status': status,
        'status_choices': [('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')],
    }
    return render(request, 'backtesting/backtest_list.html', context)


@login_required
def backtest_detail(request, backtest_id):
    """Display backtest details and results"""
    backtest = get_object_or_404(BacktestResult, id=backtest_id, created_by=request.user)
    
    # Get all trades for statistics calculation (before slicing)
    all_trades = backtest.trades.all().order_by('-timestamp')
    
    # Calculate trade statistics from all trades
    trade_stats = {
        'total_trades': all_trades.count(),
        'winning_trades': all_trades.filter(profit_loss__gt=0).count(),
        'losing_trades': all_trades.filter(profit_loss__lt=0).count(),
        'neutral_trades': all_trades.filter(profit_loss=0).count(),
    }
    
    # Add win rate calculation
    if trade_stats['total_trades'] > 0:
        trade_stats['win_rate'] = (trade_stats['winning_trades'] / trade_stats['total_trades']) * 100
    else:
        trade_stats['win_rate'] = 0
    
    # Add total profit/loss
    total_profit_loss = all_trades.aggregate(
        total=Sum('profit_loss')
    )['total'] or 0
    trade_stats['total_profit_loss'] = total_profit_loss
    
    # Get latest trades for display (after calculating stats)
    trades = all_trades[:50]  # Latest 50 trades
    
    # Calculate additional metrics for display
    performance_metrics = {
        'total_return_percent': (backtest.total_return * 100) if backtest.total_return else 0,
        'sharpe_ratio': backtest.sharpe_ratio or 0,
        'max_drawdown_percent': (backtest.max_drawdown * 100) if backtest.max_drawdown else 0,
        'volatility_percent': (backtest.volatility * 100) if backtest.volatility else 0,
        'win_rate_percent': backtest.win_rate or 0,
    }
    
    context = {
        'backtest': backtest,
        'trades': trades,
        'trade_stats': trade_stats,
        'performance_metrics': performance_metrics,
    }
    return render(request, 'backtesting/backtest_detail.html', context)


@login_required
def dashboard(request):
    """Enhanced backtesting dashboard with overview statistics"""
    user_strategies = TradingStrategy.objects.filter(created_by=request.user)
    user_backtests = BacktestResult.objects.filter(created_by=request.user)
    
    # Calculate statistics
    total_strategies = user_strategies.count()
    total_backtests = user_backtests.count()
    successful_backtests = user_backtests.filter(status='completed').count()
    active_backtests = user_backtests.filter(status__in=['pending', 'running']).count()
    
    # Recent activity
    recent_strategies = user_strategies[:5]
    recent_backtests = user_backtests[:5]
    
    # Performance metrics
    avg_return = user_backtests.filter(status='completed').aggregate(Avg('total_return'))['total_return__avg'] or 0
    best_backtest = user_backtests.filter(status='completed').order_by('-total_return').first()
    
    # Strategy type distribution
    strategy_types = user_strategies.values('strategy_type').annotate(count=Count('strategy_type'))
    
    context = {
        'total_strategies': total_strategies,
        'total_backtests': total_backtests,
        'successful_backtests': successful_backtests,
        'active_backtests': active_backtests,
        'recent_strategies': recent_strategies,
        'recent_backtests': recent_backtests,
        'avg_return': avg_return * 100 if avg_return else 0,
        'best_backtest': best_backtest,
        'strategy_types': strategy_types,
    }
    return render(request, 'backtesting/dashboard.html', context)


# Mock functions removed - now using real backtesting engine from utils


@login_required
@require_http_methods(["GET"])
def get_symbols(request):
    """API endpoint to get available symbols"""
    symbols = Symbol.objects.filter(is_active=True).values('id', 'symbol', 'name', 'exchange')
    return JsonResponse({'symbols': list(symbols)})


@login_required
@require_http_methods(["GET"])
def get_indicators(request):
    """API endpoint to get available indicators"""
    indicators = TechnicalIndicator.objects.filter(is_active=True).values(
        'id', 'name', 'indicator_type', 'description'
    )
    return JsonResponse({'indicators': list(indicators)})


@login_required
@require_http_methods(["GET"])
def get_strategy_preview(request):
    """HTMX endpoint to get strategy preview details"""
    strategy_id = request.GET.get('strategy_id')
    if not strategy_id:
        return JsonResponse({'error': 'No strategy ID provided'}, status=400)
    
    try:
        strategy = get_object_or_404(TradingStrategy, id=strategy_id, created_by=request.user)
        return render(request, 'backtesting/partials/strategy_preview.html', {
            'strategy': strategy
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required
@require_http_methods(["GET"])
def backtest_status(request, backtest_id):
    """HTMX endpoint to check backtest status"""
    backtest = get_object_or_404(BacktestResult, id=backtest_id, created_by=request.user)
    
    if request.headers.get('HX-Request'):
        return render(request, 'backtesting/partials/backtest_status.html', {
            'backtest': backtest
        })
    
    return JsonResponse({
        'status': backtest.status,
        'error_message': backtest.error_message,
        'execution_time': backtest.execution_time,
        'total_return': backtest.total_return,
        'total_trades': backtest.total_trades,
    })


@login_required 
def strategy_rules_edit(request, strategy_id):
    """Edit strategy rules"""
    strategy = get_object_or_404(TradingStrategy, id=strategy_id, created_by=request.user)
    
    if request.method == 'POST':
        # Handle rule creation/editing logic here
        action = request.POST.get('action')
        
        if action == 'add_rule':
            rule_type = request.POST.get('rule_type')
            rule_name = request.POST.get('rule_name')
            indicator_1 = request.POST.get('indicator_1')
            condition = request.POST.get('condition')
            indicator_2 = request.POST.get('indicator_2')
            value_1 = request.POST.get('value_1')
            value_2 = request.POST.get('value_2')
            
            try:
                rule = StrategyRule.objects.create(
                    name=rule_name,
                    rule_type=rule_type,
                    indicator_1=indicator_1,
                    condition=condition,
                    indicator_2=indicator_2 if indicator_2 else None,
                    value_1=float(value_1) if value_1 else None,
                    value_2=float(value_2) if value_2 else None,
                    order=0
                )
                
                if rule_type == 'buy':
                    strategy.buy_rules.add(rule)
                else:
                    strategy.sell_rules.add(rule)
                
                messages.success(request, f'Rule "{rule_name}" added successfully!')
                
            except Exception as e:
                logger.error(f"Error creating rule: {e}")
                messages.error(request, f'Error creating rule: {str(e)}')
        
        elif action == 'delete_rule':
            rule_id = request.POST.get('rule_id')
            try:
                rule = StrategyRule.objects.get(id=rule_id)
                rule_name = rule.name
                rule.delete()
                messages.success(request, f'Rule "{rule_name}" deleted successfully!')
            except StrategyRule.DoesNotExist:
                messages.error(request, 'Rule not found.')
            except Exception as e:
                logger.error(f"Error deleting rule: {e}")
                messages.error(request, f'Error deleting rule: {str(e)}')
        
        return redirect('backtesting:strategy_rules_edit', strategy.id)
    
    buy_rules = strategy.get_buy_rules_list()
    sell_rules = strategy.get_sell_rules_list()
    
    # Define indicator choices for the template
    indicator_choices = [
        ('price', 'Current Price'),
        ('sma_fast', 'SMA Fast'),
        ('sma_slow', 'SMA Slow'),
        ('rsi', 'RSI'),
        ('macd', 'MACD Line'),
        ('macd_signal', 'MACD Signal'),
        ('bb_upper', 'Bollinger Upper Band'),
        ('bb_lower', 'Bollinger Lower Band'),
        ('bb_middle', 'Bollinger Middle Band'),
        ('volume', 'Volume'),
    ]
    
    condition_choices = [
        ('crossover_above', 'Crosses Above'),
        ('crossover_below', 'Crosses Below'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
    ]
    
    context = {
        'strategy': strategy,
        'buy_rules': buy_rules,
        'sell_rules': sell_rules,
        'indicator_choices': indicator_choices,
        'condition_choices': condition_choices,
    }
    return render(request, 'backtesting/strategy_rules_edit.html', context)


@login_required
def backtest_restart(request, backtest_id):
    """Restart a failed backtest"""
    backtest = get_object_or_404(BacktestResult, id=backtest_id, created_by=request.user)
    
    if backtest.status not in ['failed', 'completed']:
        messages.error(request, 'Only failed or completed backtests can be restarted.')
        return redirect('backtesting:backtest_detail', backtest.id)
    
    if request.method == 'POST':
        try:
            # Reset backtest status
            backtest.status = 'pending'
            backtest.error_message = ''
            backtest.execution_time = None
            backtest.completed_at = None
            
            # Clear previous results but keep the backtest record
            Trade.objects.filter(backtest=backtest).delete()
            backtest.final_capital = None
            backtest.total_return = None
            backtest.sharpe_ratio = None
            backtest.max_drawdown = None
            backtest.volatility = None
            backtest.total_trades = None
            backtest.win_rate = None
            backtest.best_trade = None
            backtest.worst_trade = None
            backtest.avg_trade = None
            
            backtest.save()
            
            # Start the backtest process
            run_strategy_backtest(backtest.id)
            messages.success(request, 'Backtest restarted successfully!')
            
        except Exception as e:
            logger.error(f"Error restarting backtest: {e}")
            messages.error(request, f'Error restarting backtest: {str(e)}')
        
        return redirect('backtesting:backtest_detail', backtest.id)
    
    return redirect('backtesting:backtest_detail', backtest.id)


@login_required
def strategy_clone(request, strategy_id):
    """Clone an existing strategy"""
    original_strategy = get_object_or_404(TradingStrategy, id=strategy_id, created_by=request.user)
    
    try:
        # Create a new strategy with cloned data
        cloned_strategy = TradingStrategy.objects.create(
            name=f"{original_strategy.name} (Copy)",
            description=f"Copy of {original_strategy.description}",
            strategy_type=original_strategy.strategy_type,
            stop_loss_percent=original_strategy.stop_loss_percent,
            take_profit_percent=original_strategy.take_profit_percent,
            max_position_size=original_strategy.max_position_size,
            commission_rate=original_strategy.commission_rate,
            slippage_rate=original_strategy.slippage_rate,
            indicator_config=original_strategy.indicator_config,
            created_by=request.user
        )
        
        # Clone symbols
        cloned_strategy.symbols.set(original_strategy.symbols.all())
        
        # Clone buy rules
        for rule in original_strategy.buy_rules.all():
            new_rule = StrategyRule.objects.create(
                name=f"{rule.name} (Copy)",
                rule_type=rule.rule_type,
                indicator_1=rule.indicator_1,
                condition=rule.condition,
                indicator_2=rule.indicator_2,
                value_1=rule.value_1,
                value_2=rule.value_2,
                order=rule.order
            )
            cloned_strategy.buy_rules.add(new_rule)
        
        # Clone sell rules
        for rule in original_strategy.sell_rules.all():
            new_rule = StrategyRule.objects.create(
                name=f"{rule.name} (Copy)",
                rule_type=rule.rule_type,
                indicator_1=rule.indicator_1,
                condition=rule.condition,
                indicator_2=rule.indicator_2,
                value_1=rule.value_1,
                value_2=rule.value_2,
                order=rule.order
            )
            cloned_strategy.sell_rules.add(new_rule)
        
        messages.success(request, f'Strategy "{cloned_strategy.name}" cloned successfully!')
        return redirect('backtesting:strategy_detail', cloned_strategy.id)
        
    except Exception as e:
        logger.error(f"Error cloning strategy: {e}")
        messages.error(request, f'Error cloning strategy: {str(e)}')
        return redirect('backtesting:strategy_detail', original_strategy.id)
