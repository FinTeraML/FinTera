from django.core.management.base import BaseCommand
from backtesting.utils import DataFetcher, TechnicalIndicators
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Simple debug test'
    
    def handle(self, *args, **options):
        self.stdout.write('Testing data fetch...')
        try:
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=30)
            
            data_fetcher = DataFetcher()
            data = data_fetcher.fetch_data(['AAPL'], str(start_date), str(end_date))
            
            if data:
                df = data.get('AAPL')
                if df is not None:
                    self.stdout.write(f'Success: Got {len(df)} rows of data')
                    self.stdout.write(f'Date range: {df.index.min()} to {df.index.max()}')
                    
                    # Test SMA
                    close = df['close']
                    sma20 = TechnicalIndicators.sma(close, 20)
                    sma50 = TechnicalIndicators.sma(close, 50)
                    
                    crossovers = ((sma20.shift(1) <= sma50.shift(1)) & (sma20 > sma50)).sum()
                    self.stdout.write(f'SMA crossovers: {crossovers}')
                else:
                    self.stdout.write('No AAPL data')
            else:
                self.stdout.write('No data fetched')
                
        except Exception as e:
            self.stdout.write(f'Error: {e}')
            import traceback
            traceback.print_exc()

