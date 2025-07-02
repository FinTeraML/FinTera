from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class Symbol(models.Model):
    """Model to store available trading symbols"""
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=50, default='NASDAQ')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"
    
    class Meta:
        ordering = ['symbol']


class TechnicalIndicator(models.Model):
    """Model to store technical indicator configurations"""
    INDICATOR_TYPES = [
        ('sma', 'Simple Moving Average'),
        ('ema', 'Exponential Moving Average'),
        ('rsi', 'Relative Strength Index'),
        ('macd', 'MACD'),
        ('bollinger', 'Bollinger Bands'),
        ('stochastic', 'Stochastic Oscillator'),
        ('williams_r', 'Williams %R'),
        ('atr', 'Average True Range'),
    ]
    
    name = models.CharField(max_length=100)
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_TYPES)
    parameters = models.JSONField(default=dict, help_text="JSON parameters for the indicator")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_indicator_type_display()} - {self.name}"
    
    class Meta:
        ordering = ['indicator_type', 'name']


class StrategyRule(models.Model):
    """Model to store individual trading rules for strategies"""
    RULE_TYPES = [
        ('buy', 'Buy Rule'),
        ('sell', 'Sell Rule'),
    ]
    
    CONDITION_TYPES = [
        ('crossover_above', 'Crosses Above'),
        ('crossover_below', 'Crosses Below'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('between', 'Between'),
        ('outside', 'Outside Range'),
    ]
    
    name = models.CharField(max_length=200)
    rule_type = models.CharField(max_length=4, choices=RULE_TYPES)
    indicator_1 = models.CharField(max_length=50, help_text="First indicator (e.g., 'sma_20', 'rsi', 'price')")
    condition = models.CharField(max_length=20, choices=CONDITION_TYPES)
    indicator_2 = models.CharField(max_length=50, blank=True, help_text="Second indicator or value (e.g., 'sma_50', '70', 'price')")
    value_1 = models.FloatField(null=True, blank=True, help_text="First threshold value")
    value_2 = models.FloatField(null=True, blank=True, help_text="Second threshold value (for between/outside)")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Rule execution order")
    
    def __str__(self):
        return f"{self.rule_type.upper()}: {self.name}"
    
    class Meta:
        ordering = ['rule_type', 'order']


class TradingStrategy(models.Model):
    """Enhanced model to store complete trading strategies"""
    STRATEGY_TYPES = [
        ('momentum', 'Momentum'),
        ('mean_reversion', 'Mean Reversion'),
        ('arbitrage', 'Arbitrage'),
        ('ml_based', 'ML Based'),
        ('technical', 'Technical Analysis'),
        ('custom', 'Custom Strategy'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPES)
    symbols = models.ManyToManyField(Symbol, related_name='strategies')
    
    # Enhanced strategy configuration
    indicator_config = models.JSONField(default=dict, help_text="Indicator configurations")
    buy_rules = models.ManyToManyField(StrategyRule, related_name='buy_strategies', 
                                     limit_choices_to={'rule_type': 'buy'}, blank=True)
    sell_rules = models.ManyToManyField(StrategyRule, related_name='sell_strategies', 
                                      limit_choices_to={'rule_type': 'sell'}, blank=True)
    
    # Risk management
    stop_loss_percent = models.FloatField(default=5.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    take_profit_percent = models.FloatField(default=10.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_position_size = models.FloatField(default=0.1, validators=[MinValueValidator(0.01), MaxValueValidator(1.0)],
                                        help_text="Maximum position size as percentage of capital")
    
    # Portfolio settings
    commission_rate = models.FloatField(default=0.001, validators=[MinValueValidator(0), MaxValueValidator(0.1)])
    slippage_rate = models.FloatField(default=0.001, validators=[MinValueValidator(0), MaxValueValidator(0.1)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    
    def get_indicator_config(self):
        """Get indicator configuration with defaults"""
        default_config = {
            'sma_fast': 20,
            'sma_slow': 50,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0
        }
        return {**default_config, **self.indicator_config}
    
    def get_buy_rules_list(self):
        """Get active buy rules ordered by priority"""
        return self.buy_rules.filter(is_active=True).order_by('order')
    
    def get_sell_rules_list(self):
        """Get active sell rules ordered by priority"""
        return self.sell_rules.filter(is_active=True).order_by('order')
    
    @property
    def latest_backtest(self):
        """Get the most recent backtest for this strategy"""
        return self.backtests.filter(status='completed').order_by('-created_at').first()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Trading Strategies'


class BacktestResult(models.Model):
    """Model to store backtest results"""
    name = models.CharField(max_length=200)
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE, related_name='backtests')
    
    # Backtest parameters
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Results
    final_capital = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_return = models.FloatField(null=True, blank=True)
    sharpe_ratio = models.FloatField(null=True, blank=True)
    max_drawdown = models.FloatField(null=True, blank=True)
    win_rate = models.FloatField(null=True, blank=True)
    total_trades = models.IntegerField(null=True, blank=True, default=0)
    
    # Additional metrics
    volatility = models.FloatField(null=True, blank=True)
    best_trade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    worst_trade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_trade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Additional performance metrics
    calmar_ratio = models.FloatField(null=True, blank=True)
    sortino_ratio = models.FloatField(null=True, blank=True)
    profit_factor = models.FloatField(null=True, blank=True)
    max_consecutive_wins = models.IntegerField(null=True, blank=True)
    max_consecutive_losses = models.IntegerField(null=True, blank=True)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    error_message = models.TextField(blank=True, help_text="Error details if backtest failed")
    execution_time = models.FloatField(null=True, blank=True, help_text="Execution time in seconds")
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name} - {self.strategy.name}"
    
    @property
    def profit_loss(self):
        """Calculate profit/loss amount"""
        if self.final_capital is not None and self.initial_capital is not None:
            return self.final_capital - self.initial_capital
        return 0
    
    @property
    def return_percentage(self):
        """Calculate return percentage"""
        if self.total_return is not None:
            return self.total_return * 100
        return 0
    
    class Meta:
        ordering = ['-created_at']


class Trade(models.Model):
    """Model to store individual trades from backtests"""
    TRADE_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    
    backtest = models.ForeignKey(BacktestResult, on_delete=models.CASCADE, related_name='trades')
    symbol = models.CharField(max_length=10)
    trade_type = models.CharField(max_length=4, choices=TRADE_TYPES)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField()
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Additional trade details
    signal = models.CharField(max_length=100, blank=True, help_text="Signal that triggered this trade")
    commission = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    portfolio_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    position_size = models.FloatField(null=True, blank=True, help_text="Position size as percentage of portfolio")
    
    def __str__(self):
        return f"{self.trade_type.upper()} {self.quantity} {self.symbol} @ {self.price}"
    
    @property
    def total_value(self):
        return self.quantity * self.price
    
    class Meta:
        ordering = ['timestamp']
