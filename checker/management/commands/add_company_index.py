"""
Add GIN index on companies JSONB field for better performance
"""
from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add GIN index on LocationGroup.companies for better query performance'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if index already exists
            cursor.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'checker_locationgroup' 
                AND indexname = 'idx_locationgroup_companies_gin'
            """)
            
            if cursor.fetchone():
                self.stdout.write(self.style.WARNING('Index already exists'))
                return
            
            # Create GIN index for JSONB companies field
            self.stdout.write('Creating GIN index on companies field...')
            cursor.execute("""
                CREATE INDEX CONCURRENTLY idx_locationgroup_companies_gin 
                ON checker_locationgroup USING gin (companies)
            """)
            
            self.stdout.write(self.style.SUCCESS('Successfully created GIN index on companies field'))
            
            # Also create index on is_active for faster filtering
            cursor.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'checker_locationgroup' 
                AND indexname = 'idx_locationgroup_is_active'
            """)
            
            if not cursor.fetchone():
                self.stdout.write('Creating index on is_active field...')
                cursor.execute("""
                    CREATE INDEX CONCURRENTLY idx_locationgroup_is_active 
                    ON checker_locationgroup (is_active)
                """)
                self.stdout.write(self.style.SUCCESS('Successfully created index on is_active field'))