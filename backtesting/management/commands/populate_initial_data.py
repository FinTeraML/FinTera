from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from backtesting.models import Symbol, TechnicalIndicator, TradingStrategy, StrategyRule
from backtesting.utils import populate_initial_symbols, populate_initial_indicators
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate initial data for backtesting app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            action='store_true',
            help='Populate initial symbols',
        )
        parser.add_argument(
            '--indicators',
            action='store_true',
            help='Populate initial technical indicators',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Populate all initial data',
        )

    def handle(self, *args, **options):
        if options['all'] or options['symbols']:
            self.stdout.write('Populating symbols...')
            symbols_created = populate_initial_symbols()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {symbols_created} symbols')
            )

        if options['all'] or options['indicators']:
            self.stdout.write('Populating technical indicators...')
            indicators_created = populate_initial_indicators()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {indicators_created} indicators')
            )

        if options['all']:
            self.stdout.write('All initial data populated successfully!')
        
        # Show current counts
        symbol_count = Symbol.objects.filter(is_active=True).count()
        indicator_count = TechnicalIndicator.objects.filter(is_active=True).count()
        
        self.stdout.write(f'\nCurrent data counts:')
        self.stdout.write(f'  Active symbols: {symbol_count}')
        self.stdout.write(f'  Active indicators: {indicator_count}') 