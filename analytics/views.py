from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .utils import get_stock_data, apply_technical_indicators
from .forms import UserStrategyForm
from .models import UserStrategy
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.offline as opy
import json
import pandas as pd

@login_required
def main_panel(request):
    context = {}
    # Determine if the request is for fetching/displaying stock data or managing strategies
    # This will primarily be for HTMX partial updates to the #stock-data-display div
    # We will use GET parameters for applying strategy to simplify HTMX from list.

    # Handling for applying strategy via GET from the strategy list
    # This means a stock symbol must also be present (could be from existing context or passed)
    if request.method == 'GET' and request.htmx and request.GET.get('strategy_id') and request.GET.get('stock_symbol'):
        action = 'fetch_stock' # Treat as fetch_stock but with strategy
        stock_symbol = request.GET.get('stock_symbol', '').upper()
        strategy_id = request.GET.get('strategy_id')
        # Fall through to the main 'fetch_stock' logic below, strategy_id will be picked up
    elif request.method == 'POST': # Standard POST for fetching stock or creating strategy
        action = request.POST.get('action')
        stock_symbol = request.POST.get('stock_symbol', '').upper()
        strategy_id = request.POST.get('strategy_id') # Could be from a hidden field if form submitted
    else: # Initial GET or non-HTMX GET
        action = None # No specific action, just load main page
        stock_symbol = request.GET.get('stock_symbol', '').upper() # Allow pre-filling symbol via GET
        strategy_id = request.GET.get('strategy_id')


    if action == 'fetch_stock':
        if not stock_symbol:
            context['error_message'] = "Stock symbol cannot be empty."
            return render(request, 'analytics/_stock_data_display.html', context, status=400)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        stock_data_df = get_stock_data(stock_symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

        applied_strategy_name = None
        if stock_data_df is not None and not stock_data_df.empty:
            context['stock_symbol'] = stock_symbol # For the template to know current symbol

            # Apply strategy if strategy_id is provided
            if strategy_id:
                try:
                    strategy_obj = get_object_or_404(UserStrategy, id=strategy_id, user=request.user)
                    # strategy_obj.parameters should already be a dict due to JSONField
                    strategy_params = strategy_obj.parameters

                    stock_data_df = apply_technical_indicators(stock_data_df, strategy_obj.pandasta_strategy_name, strategy_params)
                    applied_strategy_name = strategy_obj.name
                    context['success_message'] = f"Data for {stock_symbol} with strategy '{applied_strategy_name}' applied."
                except UserStrategy.DoesNotExist:
                    context['error_message'] = "Selected strategy not found."
                    # Continue to show chart without strategy
                except json.JSONDecodeError:
                    context['error_message'] = "Strategy parameters are not valid JSON."
                except Exception as e:
                    context['error_message'] = f"Error applying strategy: {str(e)}"
            else:
                 context['success_message'] = f"Successfully fetched data for {stock_symbol}."


            # Create Plotly figure
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=stock_data_df.index, y=stock_data_df['Close'], mode='lines', name='Close Price', line=dict(color='skyblue')))

            chart_title = f'{stock_symbol} Closing Prices'
            if applied_strategy_name:
                chart_title += f' with {applied_strategy_name}'

            # Add indicator lines if they exist (e.g., SMAs)
            for col in stock_data_df.columns:
                if 'SMA_' in col or 'EMA_' in col: # Add more indicator patterns if needed
                    fig.add_trace(go.Scatter(x=stock_data_df.index, y=stock_data_df[col], mode='lines', name=col, opacity=0.7))
                elif 'RSI_' in col and not parameters.get('display_rsi_plot', False): # Example: don't plot RSI on main chart unless specified
                    pass # Or plot on subplot

            # Add Buy/Sell signals if they exist
            if 'buy_signal' in stock_data_df.columns:
                buy_signals = stock_data_df[stock_data_df['buy_signal'].notna()]
                fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['buy_signal'], mode='markers',
                                         name='Buy Signal', marker=dict(color='lime', size=10, symbol='triangle-up')))
            if 'sell_signal' in stock_data_df.columns:
                sell_signals = stock_data_df[stock_data_df['sell_signal'].notna()]
                fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['sell_signal'], mode='markers',
                                         name='Sell Signal', marker=dict(color='red', size=10, symbol='triangle-down')))

            fig.update_layout(title=chart_title, xaxis_title='Date', yaxis_title='Price (USD)', template='plotly_dark', legend_title_text='Legend')
            chart_html = opy.plot(fig, auto_open=False, output_type='div', include_plotlyjs='cdn')
            context['chart_html'] = chart_html

        elif stock_data_df is not None and stock_data_df.empty:
            context['error_message'] = f"No data found for symbol '{stock_symbol}'. It might be an invalid symbol or delisted."
        else: # Error fetching data
            context['error_message'] = f"Error fetching data for symbol '{stock_symbol}'."

        return render(request, 'analytics/_stock_data_display.html', context)

    elif action == 'create_strategy':
        form = UserStrategyForm(request.POST)
        if form.is_valid():
            try:
                strategy_params_str = form.cleaned_data.get('parameters')
                try:
                    # Validate JSON format for parameters before saving
                    json.loads(strategy_params_str)
                except json.JSONDecodeError:
                    form.add_error('parameters', 'Invalid JSON format. Please ensure keys and strings are double-quoted.')
                    # Re-render form with this specific error
                    context['strategy_form'] = form
                    return render(request, 'analytics/_user_strategy_form.html', context, status=400)

                strategy = form.save(commit=False)
                strategy.user = request.user
                # The parameters field on model is JSONField, so it will store the string as JSON.
                # If parameters were entered as '{"length": 20}', it's already a string.
                # If your form widget for parameters returns a dict, ensure it's converted to string if model expects string.
                # Here, UserStrategyForm uses a Textarea for parameters, so it's already a string.
                strategy.save()
                context['success_message'] = "Strategy saved successfully!"
                user_strategies = UserStrategy.objects.filter(user=request.user).order_by('-id')
                context['user_strategies'] = user_strategies
                return render(request, 'analytics/_user_strategies_list.html', context)
            except Exception as e:
                context['form_error_message'] = f"Error saving strategy: {str(e)}"
                context['strategy_form'] = form
                return render(request, 'analytics/_user_strategy_form.html', context, status=400)
        else: # Form is not valid
            context['strategy_form'] = form
            return render(request, 'analytics/_user_strategy_form.html', context, status=400)

    # Initial GET request or if action is None
    strategy_form = UserStrategyForm()
    user_strategies = UserStrategy.objects.filter(user=request.user).order_by('-id')
    context['strategy_form'] = strategy_form
    context['user_strategies'] = user_strategies
    # Pass current stock symbol if available, for "Apply Strategy" buttons
    if stock_symbol: # From GET param during initial load or kept from previous state
         context['stock_symbol'] = stock_symbol

    return render(request, 'analytics/main_panel.html', context)
