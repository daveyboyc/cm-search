from django.core.management.base import BaseCommand
from django.db import transaction
from checker.models_company import Company
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates PostgreSQL Company table from Component data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Increase output verbosity',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if companies already exist',
        )

    def handle(self, *args, **options):
        """Populate PostgreSQL Company table from Component data."""
        verbose = options.get('verbose', False)
        force_rebuild = options.get('force', False)
        
        # Check if companies already exist (unless force rebuild)
        if not force_rebuild:
            company_count = Company.objects.count()
            if company_count > 0:
                self.stdout.write(self.style.WARNING(
                    f'Company table already has {company_count} companies. '
                    f'Use --force to rebuild.'
                ))
                return
        
        start_time = time.time()
        
        try:
            # Use the class method to rebuild all data
            updated_count, deleted_count = Company.rebuild_search_data()
            
            total_time = time.time() - start_time
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully populated Company table in {total_time:.2f}s:\n'
                f'- Updated/created: {updated_count} companies\n'
                f'- Deleted: {deleted_count} companies\n'
                f'- Total companies: {Company.objects.count()}'
            ))
            
            # Test search functionality
            if verbose:
                self.stdout.write('\nTesting search functionality...')
                test_queries = ['grid', 'tata', 'vital', 'battery']
                for query in test_queries:
                    results = Company.search_companies(query, limit=5)
                    self.stdout.write(f'  "{query}": {results.count()} results')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error populating Company table: {str(e)}'))
            logger.error(f'Error in build_company_postgresql: {e}', exc_info=True)