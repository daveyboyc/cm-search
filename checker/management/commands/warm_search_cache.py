"""
Management command to pre-warm search cache for common queries
This helps avoid the 3-5 second delay for popular searches
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db.models import Q
from checker.models import LocationGroup
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Pre-warm search cache for common queries'

    def handle(self, *args, **options):
        # Common search terms that users frequently search for
        common_searches = [
            'boots', 'tesco', 'asda', 'sainsbury', 'sainsburys', 
            'battery', 'solar', 'wind', 'gas', 'diesel',
            'london', 'manchester', 'birmingham', 'glasgow',
            'ev charging', 'interconnector', 'hydro', 'biomass'
        ]
        
        self.stdout.write("Starting search cache warming...")
        total_cached = 0
        start_time = time.time()
        
        for query in common_searches:
            query_start = time.time()
            
            # Build the same query as the search view
            location_filter = (
                Q(location__icontains=query) |
                Q(county__icontains=query) |
                Q(companies__icontains=query) |
                Q(technologies__icontains=query) |
                Q(descriptions__icontains=query) |
                Q(cmu_ids__icontains=query)
            )
            
            # Execute the query and get IDs
            results = LocationGroup.objects.filter(location_filter)
            location_ids = list(results.values_list('id', flat=True)[:500])
            
            # Cache for different filter combinations
            filter_combos = [
                ('all', '', '', ''),  # No filters
                ('active', '', '', ''),  # Active only
                ('inactive', '', '', ''),  # Inactive only
            ]
            
            for status, auction, tech, company in filter_combos:
                cache_key = f"location_search:{query.lower()}:{status}:{auction}:{tech}:{company}"
                cache.set(cache_key, location_ids, timeout=3600)  # 1 hour
                total_cached += 1
            
            query_time = time.time() - query_start
            self.stdout.write(
                f"  Cached '{query}': {len(location_ids)} results in {query_time:.2f}s"
            )
        
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully warmed {total_cached} cache entries in {elapsed:.1f}s"
            )
        )
        self.stdout.write(
            "Common searches will now load instantly from cache!"
        )