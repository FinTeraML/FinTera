import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

def get_stock_data(symbol, start_date, end_date):
    """
    Fetches stock data for a given symbol and date range.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)
        if data.empty:
            print(f"No data found for symbol {symbol} between {start_date} and {end_date}. It might be an invalid symbol or delisted.")
            return None
        # Ensure columns are in expected case (yfinance sometimes returns them lowercased)
        data.columns = [col.capitalize() for col in data.columns]
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def apply_technical_indicators(df, pandasta_strategy_name, parameters):
    """
    Applies a technical indicator strategy from pandas-ta to the DataFrame
    and generates buy/sell signals.

    Args:
        df (pd.DataFrame): Input DataFrame with stock data (OHLCV).
                           Must have a DatetimeIndex and 'Open', 'High', 'Low', 'Close', 'Volume' columns.
        pandasta_strategy_name (str): The name of the pandas-ta strategy/indicator (e.g., 'sma', 'macd', 'rsi').
        parameters (dict): A dictionary of parameters for the strategy.
                           Example: {'fast': 10, 'slow': 20} for SMA.

    Returns:
        pd.DataFrame: The original DataFrame augmented with indicator columns and signal columns
                      ('buy_signal', 'sell_signal'). Signals are prices, NaNs otherwise.
    """
    if df is None or df.empty:
        print("DataFrame is empty. Cannot apply technical indicators.")
        return df

    # Ensure DataFrame has a TA strategy attribute
    if not hasattr(df, 'ta'):
        df.ta = ta.Strategy(name="CustomStrategy", ta=[]) # Initialize if not present

    df_with_indicators = df.copy()
    df_with_indicators['buy_signal'] = np.nan
    df_with_indicators['sell_signal'] = np.nan

    # --- SMA Crossover Example ---
    if pandasta_strategy_name.lower() == 'sma_crossover':
        fast_period = parameters.get('fast', 10)
        slow_period = parameters.get('slow', 20)

        if not all(isinstance(p, int) and p > 0 for p in [fast_period, slow_period]):
            print(f"Invalid SMA periods: fast={fast_period}, slow={slow_period}. Must be positive integers.")
            return df # Or raise error
        if fast_period >= slow_period:
            print(f"Fast SMA period ({fast_period}) must be less than slow SMA period ({slow_period}).")
            return df # Or raise error

        # Calculate SMAs using pandas_ta
        df_with_indicators.ta.sma(length=fast_period, append=True, col_names=(f'SMA_{fast_period}',))
        df_with_indicators.ta.sma(length=slow_period, append=True, col_names=(f'SMA_{slow_period}',))

        sma_fast_col = f'SMA_{fast_period}'
        sma_slow_col = f'SMA_{slow_period}'

        # Ensure indicator columns were added
        if sma_fast_col not in df_with_indicators.columns or sma_slow_col not in df_with_indicators.columns:
            print(f"Could not calculate SMAs. Columns {sma_fast_col} or {sma_slow_col} not found.")
            return df_with_indicators # Return with whatever was calculated

        # Generate signals
        # Previous condition: df[sma_fast_col].shift(1) < df[sma_slow_col].shift(1)
        # Current condition: df[sma_fast_col] > df[sma_slow_col]
        buy_conditions = (df_with_indicators[sma_fast_col].shift(1) < df_with_indicators[sma_slow_col].shift(1)) & \
                         (df_with_indicators[sma_fast_col] > df_with_indicators[sma_slow_col])

        sell_conditions = (df_with_indicators[sma_fast_col].shift(1) > df_with_indicators[sma_slow_col].shift(1)) & \
                          (df_with_indicators[sma_fast_col] < df_with_indicators[sma_slow_col])

        df_with_indicators.loc[buy_conditions, 'buy_signal'] = df_with_indicators['Low'][buy_conditions] * 0.98 # Place signal slightly below low
        df_with_indicators.loc[sell_conditions, 'sell_signal'] = df_with_indicators['High'][sell_conditions] * 1.02 # Place signal slightly above high

    # --- RSI Example ---
    elif pandasta_strategy_name.lower() == 'rsi_threshold':
        rsi_period = parameters.get('length', 14)
        oversold_threshold = parameters.get('oversold', 30)
        overbought_threshold = parameters.get('overbought', 70)

        if not (isinstance(rsi_period, int) and rsi_period > 0):
            print(f"Invalid RSI period: {rsi_period}. Must be a positive integer.")
            return df

        df_with_indicators.ta.rsi(length=rsi_period, append=True, col_names=(f'RSI_{rsi_period}',))
        rsi_col = f'RSI_{rsi_period}'

        if rsi_col not in df_with_indicators.columns:
            print(f"Could not calculate RSI. Column {rsi_col} not found.")
            return df_with_indicators

        buy_conditions = (df_with_indicators[rsi_col].shift(1) < oversold_threshold) & \
                         (df_with_indicators[rsi_col] > oversold_threshold)
        sell_conditions = (df_with_indicators[rsi_col].shift(1) > overbought_threshold) & \
                          (df_with_indicators[rsi_col] < overbought_threshold)

        df_with_indicators.loc[buy_conditions, 'buy_signal'] = df_with_indicators['Low'][buy_conditions] * 0.98
        df_with_indicators.loc[sell_conditions, 'sell_signal'] = df_with_indicators['High'][sell_conditions] * 1.02

    # --- MACD Example ---
    elif pandasta_strategy_name.lower() == 'macd_crossover':
        fast_period = parameters.get('fast', 12)
        slow_period = parameters.get('slow', 26)
        signal_period = parameters.get('signal', 9)

        # MACD call: df.ta.macd(fast=12, slow=26, signal=9, append=True)
        # This creates columns like 'MACD_12_26_9', 'MACDh_12_26_9' (histogram), 'MACDs_12_26_9' (signal line)
        df_with_indicators.ta.macd(fast=fast_period, slow=slow_period, signal=signal_period, append=True)

        macd_line_col = f'MACD_{fast_period}_{slow_period}_{signal_period}'
        signal_line_col = f'MACDs_{fast_period}_{slow_period}_{signal_period}'

        if macd_line_col not in df_with_indicators.columns or signal_line_col not in df_with_indicators.columns:
            print(f"Could not calculate MACD. Columns {macd_line_col} or {signal_line_col} not found.")
            return df_with_indicators

        # Buy: MACD crosses above Signal line
        buy_conditions = (df_with_indicators[macd_line_col].shift(1) < df_with_indicators[signal_line_col].shift(1)) & \
                         (df_with_indicators[macd_line_col] > df_with_indicators[signal_line_col])
        # Sell: MACD crosses below Signal line
        sell_conditions = (df_with_indicators[macd_line_col].shift(1) > df_with_indicators[signal_line_col].shift(1)) & \
                          (df_with_indicators[macd_line_col] < df_with_indicators[signal_line_col])

        df_with_indicators.loc[buy_conditions, 'buy_signal'] = df_with_indicators['Low'][buy_conditions] * 0.98
        df_with_indicators.loc[sell_conditions, 'sell_signal'] = df_with_indicators['High'][sell_conditions] * 1.02

    else:
        print(f"Strategy '{pandasta_strategy_name}' is not implemented yet.")
        # Optionally, try to dynamically call any pandas_ta method if it's simple (takes only 'length' or similar)
        # For safety, this is disabled by default. Example:
        # if hasattr(df.ta, pandasta_strategy_name.lower()):
        #     method_to_call = getattr(df.ta, pandasta_strategy_name.lower())
        #     # This is risky without knowing the method's signature and how to pass 'parameters'
        #     # method_to_call(**parameters, append=True)
        # else:
        #     print(f"Unknown strategy and not a direct pandas_ta method: {pandasta_strategy_name}")

    return df_with_indicators
