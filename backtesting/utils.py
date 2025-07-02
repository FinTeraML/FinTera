import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from .models import Symbol, TechnicalIndicator, BacktestResult, Trade, TradingStrategy, StrategyRule

logger = logging.getLogger(__name__)


def populate_initial_symbols():
    """Populate database with common trading symbols"""
    symbols_data = [
        ('AAPL', 'Apple Inc.', 'NASDAQ'),
        ('MSFT', 'Microsoft Corporation', 'NASDAQ'),
        ('GOOGL', 'Alphabet Inc.', 'NASDAQ'),
        ('AMZN', 'Amazon.com Inc.', 'NASDAQ'),
        ('TSLA', 'Tesla Inc.', 'NASDAQ'),
        ('META', 'Meta Platforms Inc.', 'NASDAQ'),
        ('NVDA', 'NVIDIA Corporation', 'NASDAQ'),
        ('SPY', 'SPDR S&P 500 ETF Trust', 'NYSE'),
        ('QQQ', 'Invesco QQQ Trust', 'NASDAQ'),
        ('VTI', 'Vanguard Total Stock Market ETF', 'NYSE'),
    ]
    
    created_count = 0
    for symbol, name, exchange in symbols_data:
        obj, created = Symbol.objects.get_or_create(
            symbol=symbol,
            defaults={'name': name, 'exchange': exchange, 'is_active': True}
        )
        if created:
            created_count += 1
    
    return created_count


def populate_initial_indicators():
    """Populate database with common technical indicators"""
    indicators_data = [
        ('SMA 20', 'sma', {'period': 20}, 'Simple Moving Average with 20-day period'),
        ('SMA 50', 'sma', {'period': 50}, 'Simple Moving Average with 50-day period'),
        ('RSI 14', 'rsi', {'period': 14}, 'Relative Strength Index with 14-day period'),
        ('MACD', 'macd', {'fast': 12, 'slow': 26, 'signal': 9}, 'Moving Average Convergence Divergence'),
    ]
    
    created_count = 0
    for name, indicator_type, parameters, description in indicators_data:
        obj, created = TechnicalIndicator.objects.get_or_create(
            name=name,
            indicator_type=indicator_type,
            defaults={'parameters': parameters, 'description': description, 'is_active': True}
        )
        if created:
            created_count += 1
    
    return created_count


class DataFetcher:
    """Handles fetching market data from yfinance"""
    
    @staticmethod
    def fetch_data(symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for given symbols"""
        logger.info(f"Fetching data for {symbols} from {start_date} to {end_date}")
        
        try:
            data = yf.download(symbols, start=start_date, end=end_date, group_by='ticker', auto_adjust=True, progress=False)
            
            print(f"DEBUG: Raw downloaded data shape: {data.shape}")
            print(f"DEBUG: Raw downloaded data columns: {data.columns}")
            print(f"DEBUG: Raw downloaded data index type: {type(data.index)}")
            print(f"DEBUG: Data has MultiIndex columns: {isinstance(data.columns, pd.MultiIndex)}")
            
            if data.empty:
                logger.error(f"No data fetched from yfinance for symbols {symbols} between {start_date} and {end_date}")
                return {}
            
            result = {}
            
            # Handle both single and multiple symbols with MultiIndex columns
            if isinstance(data.columns, pd.MultiIndex):
                # MultiIndex columns (symbol, price_type)
                print(f"DEBUG: Processing MultiIndex columns")
                for symbol in symbols:
                    try:
                        if symbol in data.columns.levels[0]:
                            df = data[symbol].copy()
                            df.index = pd.to_datetime(df.index)
                            df = df.dropna()
                            print(f"DEBUG: Multi symbol {symbol} data columns: {list(df.columns)}")
                            print(f"DEBUG: Multi symbol {symbol} data shape: {df.shape}")
                            if not df.empty:
                                result[symbol] = df.rename(columns={
                                    'Open': 'open', 'High': 'high', 'Low': 'low',
                                    'Close': 'close', 'Volume': 'volume'
                                })
                    except Exception as e:
                        logger.warning(f"Error processing {symbol}: {e}")
                        continue
            elif len(symbols) == 1:
                # Single symbol, simple columns
                symbol = symbols[0]
                if not data.empty:
                    df = pd.DataFrame(data)
                    df.index = pd.to_datetime(df.index)
                    print(f"DEBUG: Single symbol data columns: {list(df.columns)}")
                    print(f"DEBUG: Single symbol data shape: {df.shape}")
                    result[symbol] = df.rename(columns={
                        'Open': 'open', 'High': 'high', 'Low': 'low',
                        'Close': 'close', 'Volume': 'volume'
                    })
            else:
                # This case should not happen with modern yfinance, but keep for safety
                print(f"DEBUG: Unexpected data structure - no MultiIndex and multiple symbols")
                print(f"DEBUG: Data columns: {data.columns}")
                print(f"DEBUG: Data shape: {data.shape}")
            
            logger.info(f"Successfully fetched data for {len(result)} symbols")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching data for symbols {symbols}: {e}")
            return {}


def validate_strategy_rules(strategy):
    """Validate strategy rules and return any issues"""
    issues = []
    
    # Check if strategy has any rules
    buy_rules = strategy.get_buy_rules_list()
    sell_rules = strategy.get_sell_rules_list()
    
    if not buy_rules and not sell_rules:
        issues.append("Strategy has no trading rules defined")
    
    if not buy_rules:
        issues.append("Strategy has no buy rules defined")
    
    if not sell_rules:
        issues.append("Strategy has no sell rules defined")
    
    # Check if strategy has symbols
    if not strategy.symbols.exists():
        issues.append("Strategy has no trading symbols selected")
    
    # Validate indicator configuration
    config = strategy.get_indicator_config()
    if config.get('sma_fast', 0) >= config.get('sma_slow', 0):
        issues.append("Fast SMA period should be less than slow SMA period")
    
    if config.get('rsi_oversold', 0) >= config.get('rsi_overbought', 100):
        issues.append("RSI oversold level should be less than overbought level")
    
    if config.get('macd_fast', 0) >= config.get('macd_slow', 0):
        issues.append("MACD fast period should be less than slow period")
    
    return issues


def calculate_strategy_complexity_score(strategy):
    """Calculate a complexity score for the strategy"""
    score = 0
    
    # Base score for having a strategy
    score += 10
    
    # Points for rules
    score += strategy.buy_rules.count() * 5
    score += strategy.sell_rules.count() * 5
    
    # Points for symbols
    score += min(strategy.symbols.count() * 2, 20)  # Cap at 20 points
    
    # Points for risk management
    if strategy.stop_loss_percent > 0:
        score += 5
    if strategy.take_profit_percent > 0:
        score += 5
    
    # Complexity modifiers
    indicator_config = strategy.get_indicator_config()
    unique_indicators = set()
    
    for rule in list(strategy.buy_rules.all()) + list(strategy.sell_rules.all()):
        unique_indicators.add(rule.indicator_1)
        if rule.indicator_2:
            unique_indicators.add(rule.indicator_2)
    
    score += len(unique_indicators) * 3
    
    return min(score, 100)  # Cap at 100


def get_strategy_performance_summary(strategy):
    """Get a summary of strategy performance across all backtests"""
    backtests = strategy.backtests.filter(status='completed')
    
    if not backtests.exists():
        return None
    
    returns = [bt.total_return for bt in backtests if bt.total_return is not None]
    sharpe_ratios = [bt.sharpe_ratio for bt in backtests if bt.sharpe_ratio is not None]
    max_drawdowns = [bt.max_drawdown for bt in backtests if bt.max_drawdown is not None]
    
    summary = {
        'total_backtests': backtests.count(),
        'avg_return': sum(returns) / len(returns) if returns else 0,
        'best_return': max(returns) if returns else 0,
        'worst_return': min(returns) if returns else 0,
        'avg_sharpe': sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0,
        'avg_max_drawdown': sum(max_drawdowns) / len(max_drawdowns) if max_drawdowns else 0,
        'win_rate': len([r for r in returns if r > 0]) / len(returns) * 100 if returns else 0,
    }
    
    return summary


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD indicator"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        middle = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower 


class SignalGenerator:
    """Generate trading signals based on strategy rules"""
    
    def __init__(self, data: Dict[str, pd.DataFrame], strategy: TradingStrategy):
        self.data = data
        self.strategy = strategy
        self.config = strategy.get_indicator_config()
        self.indicators = {}
        self._calculate_indicators()
    
    def _calculate_indicators(self):
        """Calculate all technical indicators for all symbols"""
        for symbol, df in self.data.items():
            logger.info(f"Calculating indicators for {symbol}: df.shape={df.shape}, columns={list(df.columns) if not df.empty else 'EMPTY'}")
            if df.empty or 'close' not in df.columns:
                logger.warning(f"Skipping {symbol}: empty={df.empty}, columns={list(df.columns) if not df.empty else 'EMPTY'}")
                continue
                
            close = df['close']
            high = df['high'] if 'high' in df.columns else close
            low = df['low'] if 'low' in df.columns else close
            volume = df['volume'] if 'volume' in df.columns else pd.Series(index=close.index, data=0)
            
            indicators = {
                'price': close,
                'volume': volume,
                'sma_fast': TechnicalIndicators.sma(close, self.config.get('sma_fast', 20)),
                'sma_slow': TechnicalIndicators.sma(close, self.config.get('sma_slow', 50)),
                'rsi': TechnicalIndicators.rsi(close, self.config.get('rsi_period', 14)),
            }
            
            # MACD
            macd_line, signal_line, histogram = TechnicalIndicators.macd(
                close, 
                self.config.get('macd_fast', 12),
                self.config.get('macd_slow', 26),
                self.config.get('macd_signal', 9)
            )
            indicators['macd'] = macd_line
            indicators['macd_signal'] = signal_line
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
                close, self.config.get('bb_period', 20), self.config.get('bb_std', 2.0)
            )
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            
            self.indicators[symbol] = indicators
    
    def generate_signals(self) -> Dict[str, pd.DataFrame]:
        """Generate buy/sell signals for all symbols"""
        signals = {}
        
        for symbol in self.data.keys():
            if symbol not in self.indicators:
                logger.warning(f"No indicators calculated for symbol {symbol}")
                continue
                
            df = self.data[symbol].copy()
            df['buy_signal'] = False
            df['sell_signal'] = False
            
            buy_rules = self.strategy.get_buy_rules_list()
            sell_rules = self.strategy.get_sell_rules_list()
            
            logger.info(f"Generating signals for {symbol} with {len(buy_rules)} buy rules and {len(sell_rules)} sell rules")
            
            buy_signals_count = 0
            sell_signals_count = 0
            
            for i in range(1, len(df)):
                if self._evaluate_rules(buy_rules, symbol, i):
                    df.iloc[i, df.columns.get_loc('buy_signal')] = True
                    buy_signals_count += 1
                
                if self._evaluate_rules(sell_rules, symbol, i):
                    df.iloc[i, df.columns.get_loc('sell_signal')] = True
                    sell_signals_count += 1
            
            logger.info(f"Generated {buy_signals_count} buy signals and {sell_signals_count} sell signals for {symbol}")
            signals[symbol] = df
        
        return signals
    
    def _evaluate_rules(self, rules, symbol: str, index: int) -> bool:
        """Evaluate a set of rules for a given symbol and index"""
        if not rules:
            return False
        
        for rule in rules:
            if not self._evaluate_single_rule(rule, symbol, index):
                return False
        
        return True
    
    def _evaluate_single_rule(self, rule: StrategyRule, symbol: str, index: int) -> bool:
        """Evaluate a single rule"""
        try:
            indicators = self.indicators[symbol]
            
            current_val1 = self._get_indicator_value(indicators, rule.indicator_1, index)
            prev_val1 = self._get_indicator_value(indicators, rule.indicator_1, index - 1)
            
            if pd.isna(current_val1) or pd.isna(prev_val1):
                return False
            
            if rule.condition == 'crossover_above':
                if rule.indicator_2:
                    current_val2 = self._get_indicator_value(indicators, rule.indicator_2, index)
                    prev_val2 = self._get_indicator_value(indicators, rule.indicator_2, index - 1)
                    return prev_val1 <= prev_val2 and current_val1 > current_val2
                elif rule.value_1 is not None:
                    return prev_val1 <= rule.value_1 and current_val1 > rule.value_1
            
            elif rule.condition == 'crossover_below':
                if rule.indicator_2:
                    current_val2 = self._get_indicator_value(indicators, rule.indicator_2, index)
                    prev_val2 = self._get_indicator_value(indicators, rule.indicator_2, index - 1)
                    return prev_val1 >= prev_val2 and current_val1 < current_val2
                elif rule.value_1 is not None:
                    return prev_val1 >= rule.value_1 and current_val1 < rule.value_1
            
            elif rule.condition == 'greater_than':
                if rule.indicator_2:
                    current_val2 = self._get_indicator_value(indicators, rule.indicator_2, index)
                    return current_val1 > current_val2
                elif rule.value_1 is not None:
                    return current_val1 > rule.value_1
            
            elif rule.condition == 'less_than':
                if rule.indicator_2:
                    current_val2 = self._get_indicator_value(indicators, rule.indicator_2, index)
                    return current_val1 < current_val2
                elif rule.value_1 is not None:
                    return current_val1 < rule.value_1
        
        except Exception as e:
            logger.warning(f"Error evaluating rule {rule.name}: {e}")
            return False
        
        return False
    
    def _get_indicator_value(self, indicators: Dict, indicator_name: str, index: int) -> float:
        """Get indicator value at specific index"""
        if indicator_name not in indicators:
            return np.nan
        
        series = indicators[indicator_name]
        if index >= len(series) or index < 0:
            return np.nan
        
        return series.iloc[index] 


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, initial_cash: float = 10000, commission: float = 0.001, slippage: float = 0.001):
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.reset()
    
    def reset(self):
        """Reset the backtesting state"""
        self.cash = self.initial_cash
        self.positions = {}
        self.portfolio_value = []
        self.trades = []
    
    def run_backtest(self, strategy: TradingStrategy, start_date: str, end_date: str) -> Dict:
        """Run a complete backtest"""
        logger.info(f"Starting backtest for strategy: {strategy.name}")
        
        symbols = list(strategy.symbols.values_list('symbol', flat=True))
        if not symbols:
            raise ValueError("Strategy has no symbols selected")
        
        data_fetcher = DataFetcher()
        data = data_fetcher.fetch_data(symbols, start_date, end_date)
        
        if not data:
            raise ValueError("No data fetched for backtesting")
        
        signal_generator = SignalGenerator(data, strategy)
        signals = signal_generator.generate_signals()
        
        results = self._simulate_portfolio(signals, strategy)
        
        logger.info(f"Backtest completed for strategy: {strategy.name}")
        return results
    
    def _simulate_portfolio(self, signals: Dict[str, pd.DataFrame], strategy: TradingStrategy) -> Dict:
        """Simulate portfolio performance"""
        all_dates = set()
        for df in signals.values():
            all_dates.update(df.index)
        
        dates = sorted(all_dates)
        
        for date in dates:
            self._process_daily_signals(signals, date, strategy)
            
            portfolio_val = self.cash
            for symbol, quantity in self.positions.items():
                if quantity != 0:
                    price = self._get_price(signals, symbol, date)
                    if not pd.isna(price):
                        portfolio_val += quantity * price
            
            self.portfolio_value.append({
                'date': date,
                'value': portfolio_val,
                'cash': self.cash,
                'positions': self.positions.copy()
            })
        
        return self._calculate_results()
    
    def _process_daily_signals(self, signals: Dict[str, pd.DataFrame], date, strategy: TradingStrategy):
        """Process buy/sell signals for a given date"""
        for symbol, df in signals.items():
            if date not in df.index:
                continue
            
            row = df.loc[date]
            price = row['close']
            
            if pd.isna(price):
                continue
            
            buy_price = price * (1 + self.slippage)
            sell_price = price * (1 - self.slippage)
            
            if row.get('buy_signal', False):
                self._execute_buy(symbol, buy_price, date, strategy)
            
            if row.get('sell_signal', False):
                self._execute_sell(symbol, sell_price, date, strategy)
    
    def _execute_buy(self, symbol: str, price: float, date, strategy: TradingStrategy):
        """Execute a buy order"""
        if symbol not in self.positions:
            self.positions[symbol] = 0
        
        max_position_value = self.cash * strategy.max_position_size
        max_shares = int(max_position_value / price)
        
        if max_shares > 0:
            commission_cost = max_shares * price * self.commission
            total_cost = max_shares * price + commission_cost
            
            if self.cash >= total_cost:
                self.cash -= total_cost
                self.positions[symbol] += max_shares
                
                self.trades.append({
                    'symbol': symbol, 'type': 'buy', 'quantity': max_shares,
                    'price': price, 'date': date, 'commission': commission_cost,
                    'total_cost': total_cost
                })
    
    def _execute_sell(self, symbol: str, price: float, date, strategy: TradingStrategy):
        """Execute a sell order"""
        if symbol not in self.positions or self.positions[symbol] <= 0:
            return
        
        quantity = self.positions[symbol]
        commission_cost = quantity * price * self.commission
        total_proceeds = quantity * price - commission_cost
        
        self.cash += total_proceeds
        self.positions[symbol] = 0
        
        self.trades.append({
            'symbol': symbol, 'type': 'sell', 'quantity': quantity,
            'price': price, 'date': date, 'commission': commission_cost,
            'total_proceeds': total_proceeds
        })
    
    def _get_price(self, signals: Dict[str, pd.DataFrame], symbol: str, date) -> float:
        """Get price for a symbol on a specific date"""
        if symbol not in signals or date not in signals[symbol].index:
            return np.nan
        return signals[symbol].loc[date, 'close']
    
    def _calculate_results(self) -> Dict:
        """Calculate final backtest results"""
        if not self.portfolio_value:
            return {}
        
        final_value = self.portfolio_value[-1]['value']
        total_return = (final_value - self.initial_cash) / self.initial_cash
        
        values = [pv['value'] for pv in self.portfolio_value]
        daily_returns = np.diff(values) / values[:-1]
        
        results = {
            'initial_capital': self.initial_cash,
            'final_capital': final_value,
            'total_return': total_return,
            'total_trades': len(self.trades),
            'portfolio_history': self.portfolio_value,
            'trades': self.trades,
        }
        
        if len(daily_returns) > 0:
            results.update({
                'volatility': np.std(daily_returns) * np.sqrt(252),
                'sharpe_ratio': self._calculate_sharpe_ratio(daily_returns),
                'max_drawdown': self._calculate_max_drawdown(values),
                'win_rate': self._calculate_win_rate(),
            })
        
        return results
    
    def _calculate_sharpe_ratio(self, daily_returns) -> float:
        """Calculate Sharpe ratio"""
        if len(daily_returns) == 0 or np.std(daily_returns) == 0:
            return 0.0
        
        avg_return = np.mean(daily_returns)
        volatility = np.std(daily_returns)
        return (avg_return / volatility) * np.sqrt(252)
    
    def _calculate_max_drawdown(self, values) -> float:
        """Calculate maximum drawdown"""
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trades"""
        if len(self.trades) < 2:
            return 0.0
        
        profits = []
        buy_trades = {trade['symbol']: trade for trade in self.trades if trade['type'] == 'buy'}
        
        for trade in self.trades:
            if trade['type'] == 'sell' and trade['symbol'] in buy_trades:
                buy_trade = buy_trades[trade['symbol']]
                profit = trade['total_proceeds'] - buy_trade['total_cost']
                profits.append(profit)
        
        if not profits:
            return 0.0
        
        winning_trades = sum(1 for p in profits if p > 0)
        return (winning_trades / len(profits)) * 100


def run_strategy_backtest(backtest_id: int):
    """Run backtest for a given BacktestResult ID"""
    try:
        backtest = BacktestResult.objects.get(id=backtest_id)
        backtest.status = 'running'
        backtest.save()
        
        start_time = datetime.now()
        logger.info(f"Starting backtest {backtest_id} for strategy: {backtest.strategy.name}")
        
        engine = BacktestEngine(
            initial_cash=float(backtest.initial_capital),
            commission=backtest.strategy.commission_rate,
            slippage=backtest.strategy.slippage_rate
        )
        
        results = engine.run_backtest(
            backtest.strategy,
            backtest.start_date.strftime('%Y-%m-%d'),
            backtest.end_date.strftime('%Y-%m-%d')
        )
        
        # Update backtest with results
        backtest.final_capital = results.get('final_capital', backtest.initial_capital)
        backtest.total_return = results.get('total_return', 0.0)
        backtest.sharpe_ratio = results.get('sharpe_ratio', 0.0)
        backtest.max_drawdown = results.get('max_drawdown', 0.0)
        backtest.volatility = results.get('volatility', 0.0)
        backtest.total_trades = results.get('total_trades', 0)
        backtest.win_rate = results.get('win_rate', 0.0)
        
        # Calculate trade metrics
        trades = results.get('trades', [])
        if trades:
            sell_trades = [t for t in trades if t['type'] == 'sell']
            if sell_trades:
                profits = []
                for sell_trade in sell_trades:
                    buy_trades = [t for t in trades if t['type'] == 'buy' and t['symbol'] == sell_trade['symbol']]
                    if buy_trades:
                        buy_trade = buy_trades[-1]
                        profit = sell_trade['total_proceeds'] - buy_trade['total_cost']
                        profits.append(profit)
                
                if profits:
                    backtest.best_trade = max(profits)
                    backtest.worst_trade = min(profits)
                    backtest.avg_trade = sum(profits) / len(profits)
        
        # Save trade records
        Trade.objects.filter(backtest=backtest).delete()
        for trade_data in trades:
            Trade.objects.create(
                backtest=backtest,
                symbol=trade_data['symbol'],
                trade_type=trade_data['type'],
                quantity=trade_data['quantity'],
                price=trade_data['price'],
                timestamp=trade_data['date'],
                commission=trade_data.get('commission', 0),
                profit_loss=trade_data.get('total_proceeds', 0) - trade_data.get('total_cost', 0) if trade_data['type'] == 'sell' else 0,
                signal=f"{trade_data['type'].upper()} signal from strategy rules"
            )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        backtest.execution_time = execution_time
        backtest.status = 'completed'
        backtest.completed_at = datetime.now()
        backtest.save()
        
        logger.info(f"Backtest {backtest_id} completed successfully in {execution_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in backtest {backtest_id}: {e}")
        try:
            backtest = BacktestResult.objects.get(id=backtest_id)
            backtest.status = 'failed'
            backtest.error_message = str(e)
            backtest.save()
        except:
            pass 