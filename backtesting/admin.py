from django.contrib import admin
from .models import Symbol, TechnicalIndicator, TradingStrategy, BacktestResult, Trade, StrategyRule


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'exchange', 'is_active', 'created_at']
    list_filter = ['exchange', 'is_active', 'created_at']
    search_fields = ['symbol', 'name']
    list_editable = ['is_active']
    ordering = ['symbol']


@admin.register(TechnicalIndicator)
class TechnicalIndicatorAdmin(admin.ModelAdmin):
    list_display = ['name', 'indicator_type', 'is_active', 'created_at']
    list_filter = ['indicator_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['indicator_type', 'name']


@admin.register(StrategyRule)
class StrategyRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'indicator_1', 'condition', 'indicator_2', 'is_active', 'order']
    list_filter = ['rule_type', 'condition', 'is_active']
    search_fields = ['name', 'indicator_1', 'indicator_2']
    list_editable = ['is_active', 'order']
    ordering = ['rule_type', 'order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'rule_type', 'is_active', 'order')
        }),
        ('Rule Logic', {
            'fields': ('indicator_1', 'condition', 'indicator_2', 'value_1', 'value_2')
        }),
    )


@admin.register(TradingStrategy)
class TradingStrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'created_by', 'is_active', 'created_at']
    list_filter = ['strategy_type', 'is_active', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    filter_horizontal = ['symbols', 'buy_rules', 'sell_rules']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'strategy_type', 'is_active')
        }),
        ('Trading Configuration', {
            'fields': ('symbols', 'indicator_config')
        }),
        ('Trading Rules', {
            'fields': ('buy_rules', 'sell_rules'),
            'description': 'Select the buy and sell rules for this strategy'
        }),
        ('Risk Management', {
            'fields': ('stop_loss_percent', 'take_profit_percent', 'max_position_size'),
            'classes': ('collapse',)
        }),
        ('Portfolio Settings', {
            'fields': ('commission_rate', 'slippage_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy', 'status', 'total_return', 'sharpe_ratio', 'created_by', 'created_at']
    list_filter = ['status', 'created_at', 'strategy__strategy_type', 'created_by']
    search_fields = ['name', 'strategy__name']
    readonly_fields = ['created_at', 'completed_at', 'profit_loss', 'return_percentage', 'execution_time']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'strategy', 'status')
        }),
        ('Backtest Parameters', {
            'fields': ('start_date', 'end_date', 'initial_capital')
        }),
        ('Results', {
            'fields': ('final_capital', 'total_return', 'profit_loss', 'return_percentage')
        }),
        ('Performance Metrics', {
            'fields': ('sharpe_ratio', 'max_drawdown', 'win_rate', 'total_trades', 'volatility')
        }),
        ('Advanced Metrics', {
            'fields': ('calmar_ratio', 'sortino_ratio', 'profit_factor', 'max_consecutive_wins', 'max_consecutive_losses'),
            'classes': ('collapse',)
        }),
        ('Trade Details', {
            'fields': ('best_trade', 'worst_trade', 'avg_trade'),
            'classes': ('collapse',)
        }),
        ('Execution Info', {
            'fields': ('execution_time', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['backtest', 'symbol', 'trade_type', 'quantity', 'price', 'timestamp', 'profit_loss']
    list_filter = ['trade_type', 'symbol', 'timestamp', 'backtest__strategy__strategy_type']
    search_fields = ['symbol', 'signal', 'backtest__name']
    ordering = ['-timestamp']
    readonly_fields = ['total_value']
    
    fieldsets = (
        ('Trade Information', {
            'fields': ('backtest', 'symbol', 'trade_type', 'quantity', 'price', 'timestamp')
        }),
        ('Financial Details', {
            'fields': ('profit_loss', 'commission', 'total_value', 'portfolio_value', 'position_size')
        }),
        ('Signal Details', {
            'fields': ('signal',),
            'classes': ('collapse',)
        }),
    )
