from django.urls import path
from . import views

app_name = 'backtesting'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Strategy URLs
    path('strategies/', views.strategy_list, name='strategy_list'),
    path('strategies/create/', views.strategy_create, name='strategy_create'),
    path('strategies/<int:strategy_id>/', views.strategy_detail, name='strategy_detail'),
    path('strategies/<int:strategy_id>/rules/', views.strategy_rules_edit, name='strategy_rules_edit'),
    path('strategies/<int:strategy_id>/clone/', views.strategy_clone, name='strategy_clone'),
    
    # Backtest URLs
    path('backtests/', views.backtest_list, name='backtest_list'),
    path('backtests/create/', views.backtest_create, name='backtest_create'),
    path('backtests/create/<int:strategy_id>/', views.backtest_create, name='backtest_create_with_strategy'),
    path('backtests/<int:backtest_id>/', views.backtest_detail, name='backtest_detail'),
    path('backtests/<int:backtest_id>/restart/', views.backtest_restart, name='backtest_restart'),
    
    # API endpoints
    path('api/symbols/', views.get_symbols, name='get_symbols'),
    path('api/indicators/', views.get_indicators, name='get_indicators'),
    path('api/strategy-preview/', views.get_strategy_preview, name='get_strategy_preview'),
    path('api/backtest-status/<int:backtest_id>/', views.backtest_status, name='backtest_status'),
] 