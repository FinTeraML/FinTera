from django.contrib import admin
from .models import StockData, UserStrategy

@admin.register(StockData)
class StockDataAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume')
    list_filter = ('symbol', 'date')
    search_fields = ('symbol',)

@admin.register(UserStrategy)
class UserStrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'pandasta_strategy_name')
    list_filter = ('user', 'pandasta_strategy_name')
    search_fields = ('name', 'user__username')
