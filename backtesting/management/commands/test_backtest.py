from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from backtesting.models import TradingStrategy, BacktestResult, Symbol, StrategyRule
from backtesting.utils import run_strategy_backtest
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test the backtesting engine with a sample strategy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            default='AAPL',
            help='Symbol to test with (default: AAPL)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of days to backtest (default: 365)',
        )
        parser.add_argument(
            '--strategy',
            type=str,
            default='rsi',
            choices=['rsi', 'sma', 'bollinger'],
            help='Strategy type to test (default: rsi)',
        )

    def handle(self, *args, **options):
        symbol_name = options['symbol']
        days = options['days']
        strategy_type = options['strategy']
        
        self.stdout.write(f'Testing backtesting engine with {symbol_name} for {days} days using {strategy_type} strategy...')
        
        try:
            # Get or create a test user
            user, created = User.objects.get_or_create(
                username='test_user',
                defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
            )
            if created:
                user.set_password('testpass123')
                user.save()
            
            # Get or create symbol
            symbol, created = Symbol.objects.get_or_create(
                symbol=symbol_name,
                defaults={'name': f'{symbol_name} Inc.', 'exchange': 'NASDAQ', 'is_active': True}
            )
            
            # Create strategy based on type
            if strategy_type == 'rsi':
                strategy = self._create_rsi_strategy(user, symbol_name)
            elif strategy_type == 'sma':
                strategy = self._create_sma_strategy(user, symbol_name)
            elif strategy_type == 'bollinger':
                strategy = self._create_bollinger_strategy(user, symbol_name)
            
            # Add symbol to strategy
            strategy.symbols.add(symbol)
            
            # Create backtest - use historical dates to ensure data availability
            end_date = date(2024, 12, 31)  # Fixed historical end date
            start_date = end_date - timedelta(days=days)
            
            backtest = BacktestResult.objects.create(
                name=f'Test Backtest - {symbol_name}',
                strategy=strategy,
                start_date=start_date,
                end_date=end_date,
                initial_capital=10000.00,
                created_by=user
            )
            
            self.stdout.write(f'Created backtest #{backtest.id}')
            self.stdout.write(f'Period: {start_date} to {end_date}')
            self.stdout.write(f'Initial capital: ${backtest.initial_capital}')
            
            # Run the backtest
            self.stdout.write('Starting backtest...')
            run_strategy_backtest(backtest.id)
            
            # Refresh from database
            backtest.refresh_from_db()
            
            # Display results
            self.stdout.write(self.style.SUCCESS('\n=== BACKTEST RESULTS ==='))
            self.stdout.write(f'Status: {backtest.status}')
            
            if backtest.status == 'completed':
                self.stdout.write(f'Final Capital: ${backtest.final_capital:.2f}')
                self.stdout.write(f'Total Return: {backtest.total_return:.2%}')
                self.stdout.write(f'Total Trades: {backtest.total_trades}')
                self.stdout.write(f'Win Rate: {backtest.win_rate:.1f}%')
                self.stdout.write(f'Sharpe Ratio: {backtest.sharpe_ratio:.2f}')
                self.stdout.write(f'Max Drawdown: {backtest.max_drawdown:.2%}')
                self.stdout.write(f'Volatility: {backtest.volatility:.2%}')
                self.stdout.write(f'Execution Time: {backtest.execution_time:.2f} seconds')
                
                if backtest.best_trade:
                    self.stdout.write(f'Best Trade: ${backtest.best_trade:.2f}')
                if backtest.worst_trade:
                    self.stdout.write(f'Worst Trade: ${backtest.worst_trade:.2f}')
                if backtest.avg_trade:
                    self.stdout.write(f'Average Trade: ${backtest.avg_trade:.2f}')
                
                # Show sample trades
                trades = backtest.trades.all()[:10]
                if trades:
                    self.stdout.write('\n=== SAMPLE TRADES ===')
                    for trade in trades:
                        self.stdout.write(
                            f'{trade.timestamp.strftime("%Y-%m-%d")}: '
                            f'{trade.trade_type.upper()} {trade.quantity} {trade.symbol} @ ${trade.price:.2f}'
                        )
                
                self.stdout.write(self.style.SUCCESS('\nBacktest completed successfully!'))
            elif backtest.status == 'failed':
                self.stdout.write(self.style.ERROR(f'Backtest failed: {backtest.error_message}'))
            else:
                self.stdout.write(f'Backtest status: {backtest.status}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            logger.exception("Error in test backtest command")
    
    def _create_rsi_strategy(self, user, symbol_name):
        """Create RSI mean reversion strategy"""
        strategy_name = f'Test RSI Mean Reversion Strategy - {symbol_name}'
        strategy, created = TradingStrategy.objects.get_or_create(
            name=strategy_name,
            created_by=user,
            defaults={
                'description': 'Test RSI-based mean reversion strategy',
                'strategy_type': 'mean_reversion',
                'stop_loss_percent': 5.0,
                'take_profit_percent': 10.0,
                'max_position_size': 0.2,
                'commission_rate': 0.001,
                'slippage_rate': 0.001,
                'indicator_config': {
                    'rsi_period': 14,
                    'rsi_oversold': 30,
                    'rsi_overbought': 70
                }
            }
        )
        
        # Create strategy rules for RSI mean reversion
        buy_rule, _ = StrategyRule.objects.get_or_create(
            name=f"RSI crosses above oversold - {symbol_name}",
            rule_type='buy',
            indicator_1='rsi',
            condition='crossover_above',
            value_1=30.0,
            order=1
        )
        
        sell_rule, _ = StrategyRule.objects.get_or_create(
            name=f"RSI crosses below overbought - {symbol_name}",
            rule_type='sell',
            indicator_1='rsi',
            condition='crossover_below',
            value_1=70.0,
            order=1
        )
        
        strategy.buy_rules.add(buy_rule)
        strategy.sell_rules.add(sell_rule)
        strategy.save()
        return strategy
    
    def _create_sma_strategy(self, user, symbol_name):
        """Create SMA crossover momentum strategy"""
        strategy_name = f'Test SMA Crossover Strategy - {symbol_name}'
        strategy, created = TradingStrategy.objects.get_or_create(
            name=strategy_name,
            created_by=user,
            defaults={
                'description': 'Test SMA crossover momentum strategy',
                'strategy_type': 'momentum',
                'stop_loss_percent': 5.0,
                'take_profit_percent': 15.0,
                'max_position_size': 0.15,
                'commission_rate': 0.001,
                'slippage_rate': 0.001,
                'indicator_config': {
                    'sma_fast': 20,
                    'sma_slow': 50
                }
            }
        )
        
        # Create strategy rules for SMA crossover
        buy_rule, _ = StrategyRule.objects.get_or_create(
            name=f"SMA Fast crosses above SMA Slow - {symbol_name}",
            rule_type='buy',
            indicator_1='sma_fast',
            condition='crossover_above',
            indicator_2='sma_slow',
            order=1
        )
        
        sell_rule, _ = StrategyRule.objects.get_or_create(
            name=f"SMA Fast crosses below SMA Slow - {symbol_name}",
            rule_type='sell',
            indicator_1='sma_fast',
            condition='crossover_below',
            indicator_2='sma_slow',
            order=1
        )
        
        strategy.buy_rules.add(buy_rule)
        strategy.sell_rules.add(sell_rule)
        strategy.save()
        return strategy
    
    def _create_bollinger_strategy(self, user, symbol_name):
        """Create Bollinger Bands mean reversion strategy"""
        strategy_name = f'Test Bollinger Bands Strategy - {symbol_name}'
        strategy, created = TradingStrategy.objects.get_or_create(
            name=strategy_name,
            created_by=user,
            defaults={
                'description': 'Test Bollinger Bands mean reversion strategy',
                'strategy_type': 'mean_reversion',
                'stop_loss_percent': 4.0,
                'take_profit_percent': 8.0,
                'max_position_size': 0.25,
                'commission_rate': 0.001,
                'slippage_rate': 0.001,
                'indicator_config': {
                    'bb_period': 20,
                    'bb_std': 2.0
                }
            }
        )
        
        # Create strategy rules for Bollinger Bands
        # Buy when price crosses below lower band
        buy_rule, _ = StrategyRule.objects.get_or_create(
            name=f"Price crosses below BB Lower - {symbol_name}",
            rule_type='buy',
            indicator_1='price',
            condition='crossover_below',
            indicator_2='bb_lower',
            order=1
        )
        
        # Sell when price crosses above upper band
        sell_rule, _ = StrategyRule.objects.get_or_create(
            name=f"Price crosses above BB Upper - {symbol_name}",
            rule_type='sell',
            indicator_1='price',
            condition='crossover_above',
            indicator_2='bb_upper',
            order=1
        )
        
        strategy.buy_rules.add(buy_rule)
        strategy.sell_rules.add(sell_rule)
        strategy.save()
        return strategy 