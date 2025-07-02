from django.core.management.base import BaseCommand
from backtesting.models import Symbol, TechnicalIndicator


class Command(BaseCommand):
    help = 'Populate the database with initial symbols and technical indicators for backtesting'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate backtesting data...'))
        
        # Create popular stock symbols
        symbols_data = [
            # Technology
            ('AAPL', 'Apple Inc.', 'NASDAQ'),
            ('GOOGL', 'Alphabet Inc.', 'NASDAQ'),
            ('MSFT', 'Microsoft Corporation', 'NASDAQ'),
            ('AMZN', 'Amazon.com Inc.', 'NASDAQ'),
            ('TSLA', 'Tesla Inc.', 'NASDAQ'),
            ('META', 'Meta Platforms Inc.', 'NASDAQ'),
            ('NVDA', 'NVIDIA Corporation', 'NASDAQ'),
            ('NFLX', 'Netflix Inc.', 'NASDAQ'),
            
            # Financial
            ('JPM', 'JPMorgan Chase & Co.', 'NYSE'),
            ('BAC', 'Bank of America Corporation', 'NYSE'),
            ('WFC', 'Wells Fargo & Company', 'NYSE'),
            ('GS', 'Goldman Sachs Group Inc.', 'NYSE'),
            ('V', 'Visa Inc.', 'NYSE'),
            ('MA', 'Mastercard Incorporated', 'NYSE'),
            
            # Healthcare
            ('JNJ', 'Johnson & Johnson', 'NYSE'),
            ('PFE', 'Pfizer Inc.', 'NYSE'),
            ('UNH', 'UnitedHealth Group Incorporated', 'NYSE'),
            ('MRNA', 'Moderna Inc.', 'NASDAQ'),
            
            # Consumer Goods
            ('KO', 'The Coca-Cola Company', 'NYSE'),
            ('PEP', 'PepsiCo Inc.', 'NASDAQ'),
            ('WMT', 'Walmart Inc.', 'NYSE'),
            ('HD', 'The Home Depot Inc.', 'NYSE'),
            
            # Energy
            ('XOM', 'Exxon Mobil Corporation', 'NYSE'),
            ('CVX', 'Chevron Corporation', 'NYSE'),
            
            # ETFs
            ('SPY', 'SPDR S&P 500 ETF Trust', 'NYSE'),
            ('QQQ', 'Invesco QQQ Trust', 'NASDAQ'),
            ('IWM', 'iShares Russell 2000 ETF', 'NYSE'),
            ('VTI', 'Vanguard Total Stock Market ETF', 'NYSE'),
        ]
        
        symbols_created = 0
        for symbol, name, exchange in symbols_data:
            symbol_obj, created = Symbol.objects.get_or_create(
                symbol=symbol,
                defaults={
                    'name': name,
                    'exchange': exchange,
                    'is_active': True
                }
            )
            if created:
                symbols_created += 1
                self.stdout.write(f'Created symbol: {symbol}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {symbols_created} new symbols')
        )
        
        # Create technical indicators
        indicators_data = [
            # Moving Averages
            ('SMA 20', 'sma', 'Simple Moving Average with 20-period', {'period': 20}),
            ('SMA 50', 'sma', 'Simple Moving Average with 50-period', {'period': 50}),
            ('SMA 200', 'sma', 'Simple Moving Average with 200-period', {'period': 200}),
            ('EMA 12', 'ema', 'Exponential Moving Average with 12-period', {'period': 12}),
            ('EMA 26', 'ema', 'Exponential Moving Average with 26-period', {'period': 26}),
            
            # Momentum Indicators
            ('RSI 14', 'rsi', 'Relative Strength Index with 14-period', {'period': 14, 'overbought': 70, 'oversold': 30}),
            ('RSI 21', 'rsi', 'Relative Strength Index with 21-period', {'period': 21, 'overbought': 70, 'oversold': 30}),
            
            # MACD
            ('MACD Standard', 'macd', 'MACD with standard parameters (12, 26, 9)', {
                'fast_period': 12, 'slow_period': 26, 'signal_period': 9
            }),
            ('MACD Fast', 'macd', 'MACD with faster parameters (5, 13, 5)', {
                'fast_period': 5, 'slow_period': 13, 'signal_period': 5
            }),
            
            # Bollinger Bands
            ('Bollinger Bands 20', 'bollinger', 'Bollinger Bands with 20-period and 2 standard deviations', {
                'period': 20, 'std_dev': 2
            }),
            ('Bollinger Bands 50', 'bollinger', 'Bollinger Bands with 50-period and 2 standard deviations', {
                'period': 50, 'std_dev': 2
            }),
            
            # Stochastic
            ('Stochastic %K 14', 'stochastic', 'Stochastic Oscillator with 14-period', {
                'k_period': 14, 'd_period': 3, 'smooth_k': 3
            }),
            ('Stochastic Fast', 'stochastic', 'Fast Stochastic Oscillator', {
                'k_period': 5, 'd_period': 3, 'smooth_k': 1
            }),
            
            # Williams %R
            ('Williams %R 14', 'williams_r', 'Williams %R with 14-period', {'period': 14}),
            ('Williams %R 21', 'williams_r', 'Williams %R with 21-period', {'period': 21}),
            
            # Average True Range
            ('ATR 14', 'atr', 'Average True Range with 14-period', {'period': 14}),
            ('ATR 21', 'atr', 'Average True Range with 21-period', {'period': 21}),
        ]
        
        indicators_created = 0
        for name, indicator_type, description, parameters in indicators_data:
            indicator_obj, created = TechnicalIndicator.objects.get_or_create(
                name=name,
                indicator_type=indicator_type,
                defaults={
                    'description': description,
                    'parameters': parameters,
                    'is_active': True
                }
            )
            if created:
                indicators_created += 1
                self.stdout.write(f'Created indicator: {name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {indicators_created} new technical indicators')
        )
        
        # Summary
        total_symbols = Symbol.objects.count()
        total_indicators = TechnicalIndicator.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nData population completed successfully!\n'
                f'Total symbols in database: {total_symbols}\n'
                f'Total indicators in database: {total_indicators}'
            )
        ) 