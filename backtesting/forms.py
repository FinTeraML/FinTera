from django import forms
from django.contrib.auth.models import User
from datetime import date, timedelta
from .models import TradingStrategy, BacktestResult, Symbol, TechnicalIndicator, StrategyRule
import json
import logging

logger = logging.getLogger(__name__)


class StrategyRuleForm(forms.ModelForm):
    """Form for creating strategy rules"""
    
    class Meta:
        model = StrategyRule
        fields = ['name', 'rule_type', 'indicator_1', 'condition', 'indicator_2', 'value_1', 'value_2', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter rule name'
            }),
            'rule_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'indicator_1': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'condition': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'indicator_2': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Second indicator or leave blank'
            }),
            'value_1': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Threshold value',
                'step': '0.01'
            }),
            'value_2': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Second value (for range conditions)',
                'step': '0.01'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'value': '0'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define indicator choices
        indicator_choices = [
            ('price', 'Current Price'),
            ('sma_fast', 'SMA Fast (20)'),
            ('sma_slow', 'SMA Slow (50)'),
            ('ema_fast', 'EMA Fast (20)'),
            ('ema_slow', 'EMA Slow (50)'),
            ('rsi', 'RSI'),
            ('macd', 'MACD Line'),
            ('macd_signal', 'MACD Signal'),
            ('bb_upper', 'Bollinger Upper Band'),
            ('bb_lower', 'Bollinger Lower Band'),
            ('bb_middle', 'Bollinger Middle Band'),
            ('volume', 'Volume'),
        ]
        
        self.fields['indicator_1'].widget = forms.Select(
            choices=[('', 'Select Indicator')] + indicator_choices,
            attrs={'class': 'select select-bordered w-full'}
        )


class StrategyForm(forms.ModelForm):
    """Enhanced form for creating and editing trading strategies"""
    
    # Indicator configuration fields
    sma_fast_period = forms.IntegerField(
        initial=20, min_value=1, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    sma_slow_period = forms.IntegerField(
        initial=50, min_value=1, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    rsi_period = forms.IntegerField(
        initial=14, min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    rsi_oversold = forms.FloatField(
        initial=30, min_value=0, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm', 'step': '0.1'})
    )
    rsi_overbought = forms.FloatField(
        initial=70, min_value=50, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm', 'step': '0.1'})
    )
    macd_fast = forms.IntegerField(
        initial=12, min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    macd_slow = forms.IntegerField(
        initial=26, min_value=1, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    macd_signal = forms.IntegerField(
        initial=9, min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    bb_period = forms.IntegerField(
        initial=20, min_value=1, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm'})
    )
    bb_std = forms.FloatField(
        initial=2.0, min_value=0.1, max_value=5.0,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered input-sm', 'step': '0.1'})
    )
    
    class Meta:
        model = TradingStrategy
        fields = ['name', 'description', 'strategy_type', 'symbols', 'stop_loss_percent', 
                 'take_profit_percent', 'max_position_size', 'commission_rate', 'slippage_rate']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter strategy name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Describe your trading strategy...'
            }),
            'strategy_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'symbols': forms.CheckboxSelectMultiple(attrs={
                'class': 'checkbox'
            }),
            'stop_loss_percent': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'take_profit_percent': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'max_position_size': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0.01',
                'max': '1.0'
            }),
            'commission_rate': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.0001',
                'min': '0',
                'max': '0.1'
            }),
            'slippage_rate': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.0001',
                'min': '0',
                'max': '0.1'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['symbols'].queryset = Symbol.objects.filter(is_active=True)
        self.fields['symbols'].required = True
        
        # Load indicator config if editing existing strategy
        if self.instance.pk:
            config = self.instance.get_indicator_config()
            self.fields['sma_fast_period'].initial = config.get('sma_fast', 20)
            self.fields['sma_slow_period'].initial = config.get('sma_slow', 50)
            self.fields['rsi_period'].initial = config.get('rsi_period', 14)
            self.fields['rsi_oversold'].initial = config.get('rsi_oversold', 30)
            self.fields['rsi_overbought'].initial = config.get('rsi_overbought', 70)
            self.fields['macd_fast'].initial = config.get('macd_fast', 12)
            self.fields['macd_slow'].initial = config.get('macd_slow', 26)
            self.fields['macd_signal'].initial = config.get('macd_signal', 9)
            self.fields['bb_period'].initial = config.get('bb_period', 20)
            self.fields['bb_std'].initial = config.get('bb_std', 2.0)
        
        # Add help text
        self.fields['symbols'].help_text = "Select one or more symbols to trade"
        self.fields['stop_loss_percent'].help_text = "Automatic stop loss percentage"
        self.fields['take_profit_percent'].help_text = "Automatic take profit percentage"
        self.fields['max_position_size'].help_text = "Maximum position size as decimal (0.1 = 10%)"
    
    def save(self, commit=True):
        strategy = super().save(commit=False)
        
        # Save indicator configuration
        indicator_config = {
            'sma_fast': self.cleaned_data['sma_fast_period'],
            'sma_slow': self.cleaned_data['sma_slow_period'],
            'rsi_period': self.cleaned_data['rsi_period'],
            'rsi_oversold': self.cleaned_data['rsi_oversold'],
            'rsi_overbought': self.cleaned_data['rsi_overbought'],
            'macd_fast': self.cleaned_data['macd_fast'],
            'macd_slow': self.cleaned_data['macd_slow'],
            'macd_signal': self.cleaned_data['macd_signal'],
            'bb_period': self.cleaned_data['bb_period'],
            'bb_std': self.cleaned_data['bb_std'],
        }
        strategy.indicator_config = indicator_config
        
        if commit:
            strategy.save()
            self.save_m2m()
        return strategy
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate SMA periods
        sma_fast = cleaned_data.get('sma_fast_period')
        sma_slow = cleaned_data.get('sma_slow_period')
        if sma_fast and sma_slow and sma_fast >= sma_slow:
            raise forms.ValidationError("Fast SMA period must be less than slow SMA period")
        
        # Validate RSI thresholds
        rsi_oversold = cleaned_data.get('rsi_oversold')
        rsi_overbought = cleaned_data.get('rsi_overbought')
        if rsi_oversold and rsi_overbought and rsi_oversold >= rsi_overbought:
            raise forms.ValidationError("RSI oversold level must be less than overbought level")
        
        # Validate MACD periods
        macd_fast = cleaned_data.get('macd_fast')
        macd_slow = cleaned_data.get('macd_slow')
        if macd_fast and macd_slow and macd_fast >= macd_slow:
            raise forms.ValidationError("MACD fast period must be less than slow period")
        
        # Validate at least one symbol is selected
        symbols = cleaned_data.get('symbols')
        if not symbols:
            raise forms.ValidationError("Please select at least one trading symbol")
        
        return cleaned_data


class QuickStrategyForm(forms.Form):
    """Quick strategy creation form with predefined templates"""
    
    STRATEGY_TEMPLATES = [
        ('sma_crossover', 'SMA Crossover (20/50)'),
        ('rsi_oversold', 'RSI Oversold/Overbought'),
        ('macd_momentum', 'MACD Momentum'),
        ('bollinger_mean_reversion', 'Bollinger Bands Mean Reversion'),
        ('custom', 'Custom Strategy'),
    ]
    
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter strategy name'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Brief strategy description...'
        }),
        required=False
    )
    
    template = forms.ChoiceField(
        choices=STRATEGY_TEMPLATES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )
    
    symbols = forms.ModelMultipleChoiceField(
        queryset=Symbol.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'checkbox'
        })
    )
    
    def create_strategy_from_template(self, user):
        """Create a strategy based on the selected template"""
        template = self.cleaned_data['template']
        name = self.cleaned_data['name']
        description = self.cleaned_data['description']
        symbols = self.cleaned_data['symbols']
        
        # Validate unique name for this user
        if TradingStrategy.objects.filter(name=name, created_by=user).exists():
            raise forms.ValidationError(f"You already have a strategy named '{name}'")
        
        # Validate symbol selection
        if len(symbols) == 0:
            raise forms.ValidationError("Please select at least one trading symbol")
        
        if len(symbols) > 20:
            raise forms.ValidationError("Too many symbols selected. Please limit to 20 symbols for optimal performance")
        
        # Create base strategy
        strategy = TradingStrategy.objects.create(
            name=name,
            description=description or f"Auto-generated {template.replace('_', ' ').title()} strategy",
            strategy_type='technical',
            created_by=user
        )
        strategy.symbols.set(symbols)
        
        # Create rules based on template
        if template == 'sma_crossover':
            strategy.strategy_type = 'momentum'
            strategy.description = description or "Buy when fast SMA crosses above slow SMA, sell when fast SMA crosses below slow SMA"
            
            buy_rule = StrategyRule.objects.create(
                name="SMA Fast crosses above SMA Slow",
                rule_type='buy',
                indicator_1='sma_fast',
                condition='crossover_above',
                indicator_2='sma_slow',
                order=1
            )
            sell_rule = StrategyRule.objects.create(
                name="SMA Fast crosses below SMA Slow",
                rule_type='sell',
                indicator_1='sma_fast',
                condition='crossover_below',
                indicator_2='sma_slow',
                order=1
            )
            strategy.buy_rules.add(buy_rule)
            strategy.sell_rules.add(sell_rule)
            
        elif template == 'rsi_oversold':
            strategy.strategy_type = 'mean_reversion'
            strategy.description = description or "Buy when RSI indicates oversold conditions, sell when RSI indicates overbought conditions"
            
            buy_rule = StrategyRule.objects.create(
                name="RSI crosses above oversold level",
                rule_type='buy',
                indicator_1='rsi',
                condition='crossover_above',
                value_1=30,
                order=1
            )
            sell_rule = StrategyRule.objects.create(
                name="RSI crosses below overbought level",
                rule_type='sell',
                indicator_1='rsi',
                condition='crossover_below',
                value_1=70,
                order=1
            )
            strategy.buy_rules.add(buy_rule)
            strategy.sell_rules.add(sell_rule)
            
        elif template == 'macd_momentum':
            strategy.strategy_type = 'momentum'
            strategy.description = description or "Buy when MACD line crosses above signal line, sell when MACD line crosses below signal line"
            
            buy_rule = StrategyRule.objects.create(
                name="MACD crosses above signal line",
                rule_type='buy',
                indicator_1='macd',
                condition='crossover_above',
                indicator_2='macd_signal',
                order=1
            )
            sell_rule = StrategyRule.objects.create(
                name="MACD crosses below signal line",
                rule_type='sell',
                indicator_1='macd',
                condition='crossover_below',
                indicator_2='macd_signal',
                order=1
            )
            strategy.buy_rules.add(buy_rule)
            strategy.sell_rules.add(sell_rule)
            
        elif template == 'bollinger_mean_reversion':
            strategy.strategy_type = 'mean_reversion'
            strategy.description = description or "Buy when price touches lower Bollinger Band, sell when price touches upper Bollinger Band"
            
            buy_rule = StrategyRule.objects.create(
                name="Price touches lower Bollinger Band",
                rule_type='buy',
                indicator_1='price',
                condition='less_than',
                indicator_2='bb_lower',
                order=1
            )
            sell_rule = StrategyRule.objects.create(
                name="Price touches upper Bollinger Band",
                rule_type='sell',
                indicator_1='price',
                condition='greater_than',
                indicator_2='bb_upper',
                order=1
            )
            strategy.buy_rules.add(buy_rule)
            strategy.sell_rules.add(sell_rule)
        
        # Set default risk management parameters optimized for backtesting
        strategy.stop_loss_percent = 5.0
        strategy.take_profit_percent = 10.0
        strategy.max_position_size = 0.1  # 10% max position size
        strategy.commission_rate = 0.001  # 0.1% commission
        strategy.slippage_rate = 0.001    # 0.1% slippage
        
        strategy.save()
        logger.info(f"Created strategy '{strategy.name}' from template '{template}' with {len(symbols)} symbols")
        return strategy


class BacktestForm(forms.ModelForm):
    """Enhanced form for creating backtests"""
    
    class Meta:
        model = BacktestResult
        fields = ['name', 'strategy', 'start_date', 'end_date', 'initial_capital']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter backtest name'
            }),
            'strategy': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'initial_capital': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '10000.00',
                'step': '0.01',
                'min': '100'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values
        self.fields['start_date'].initial = date.today() - timedelta(days=365)
        self.fields['end_date'].initial = date.today()
        self.fields['initial_capital'].initial = 10000.00
        
        # Add help text
        self.fields['start_date'].help_text = "Start date for the backtest period"
        self.fields['end_date'].help_text = "End date for the backtest period"
        self.fields['initial_capital'].help_text = "Initial capital amount in USD"
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        initial_capital = cleaned_data.get('initial_capital')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("End date must be after start date")
            
            if end_date > date.today():
                raise forms.ValidationError("End date cannot be in the future")
            
            if (end_date - start_date).days < 30:
                raise forms.ValidationError("Backtest period must be at least 30 days")
        
        if initial_capital and initial_capital < 100:
            raise forms.ValidationError("Initial capital must be at least $100")
        
        return cleaned_data


class SymbolSearchForm(forms.Form):
    """Form for searching symbols"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Search symbols...'
        })
    )
    exchange = forms.ChoiceField(
        choices=[('', 'All Exchanges'), ('NASDAQ', 'NASDAQ'), ('NYSE', 'NYSE'), ('AMEX', 'AMEX')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )


class TechnicalIndicatorForm(forms.ModelForm):
    """Form for creating technical indicators"""
    
    class Meta:
        model = TechnicalIndicator
        fields = ['name', 'indicator_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter indicator name'
            }),
            'indicator_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Describe the indicator configuration...'
            }),
        } 