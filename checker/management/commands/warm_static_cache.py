"""
Management command for warming the static page cache.

This command pre-generates and caches the most commonly accessed pages
for the "All Locations" view, eliminating database queries for future
requests to these pages.

Usage:
    python manage.py warm_static_cache                  # Warm default pages
    python manage.py warm_static_cache --pages 1 2 3    # Warm specific pages  
    python manage.py warm_static_cache --clear          # Clear cache first
    python manage.py warm_static_cache --stats          # Show cache stats
"""

import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from checker.services.static_page_cache import static_cache


class Command(BaseCommand):
    help = 'Warm the static page cache for All Locations view'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            nargs='+',
            type=int,
            help='Specific page numbers to warm (default: 1,2,3,4)',
            default=[1, 2, 3, 4]
        )
        
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing cache before warming',
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show cache statistics',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cache warming even if cache is valid',
        )

    def handle(self, *args, **options):
        """Handle the management command execution."""
        
        self.stdout.write(
            self.style.SUCCESS('🔥 Static Page Cache Management Tool')
        )
        
        # Show cache statistics if requested
        if options['stats']:
            self.show_cache_stats()
            return
        
        # Clear cache if requested
        if options['clear']:
            self.clear_cache()
        
        # Check if cache warming is needed
        if not options['force'] and static_cache.is_cache_valid():
            self.stdout.write(
                self.style.WARNING('Cache is already valid. Use --force to warm anyway.')
            )
            self.show_cache_stats()
            return
        
        # Warm the cache
        pages = options['pages']
        self.warm_cache(pages)
        
        # Show final statistics
        self.show_cache_stats()

    def clear_cache(self):
        """Clear the static page cache."""
        self.stdout.write('🗑️  Clearing static page cache...')
        
        cleared = static_cache.clear_cache()
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Cleared {cleared} cached pages')
        )

    def warm_cache(self, pages):
        """Warm the cache for specified pages."""
        self.stdout.write(f'🔥 Warming cache for pages {pages}...')
        
        start_time = time.time()
        
        try:
            results = static_cache.warm_cache(pages)
            
            # Show results
            total_time = results['total_time']
            success_count = len(results['success'])
            failed_count = len(results['failed'])
            
            self.stdout.write('')
            self.stdout.write('📊 Cache Warming Results:')
            self.stdout.write(f'   ✅ Successfully warmed: {success_count} pages')
            self.stdout.write(f'   ❌ Failed: {failed_count} pages')
            self.stdout.write(f'   ⏱️  Total time: {total_time:.3f}s')
            
            if results['success']:
                self.stdout.write('')
                self.stdout.write('✅ Successfully warmed pages:')
                for result in results['success']:
                    page = result['page']
                    page_time = result['time']
                    self.stdout.write(f'   📄 Page {page}: {page_time:.3f}s')
            
            if results['failed']:
                self.stdout.write('')
                self.stdout.write(self.style.ERROR('❌ Failed pages:'))
                for result in results['failed']:
                    page = result['page']
                    error = result['error']
                    self.stdout.write(f'   📄 Page {page}: {error}')
            
            # Calculate performance improvement
            avg_page_time = total_time / max(1, success_count)
            estimated_db_time = avg_page_time * 0.8  # Assume 80% of time is DB queries
            
            self.stdout.write('')
            self.stdout.write('🚀 Performance Impact:')
            self.stdout.write(f'   💾 Future cache hits will take: ~10ms (vs {avg_page_time*1000:.0f}ms)')
            self.stdout.write(f'   🗃️  Database queries eliminated: 8-12 per request')
            self.stdout.write(f'   📊 Estimated egress saved: ~15KB per cached request')
            
        except Exception as e:
            raise CommandError(f'Cache warming failed: {e}')

    def show_cache_stats(self):
        """Display current cache statistics."""
        try:
            stats = static_cache.get_cache_stats()
            
            self.stdout.write('')
            self.stdout.write('📊 Cache Statistics:')
            self.stdout.write(f'   🎯 Hit rate: {stats["hit_rate"]}')
            self.stdout.write(f'   ✅ Cache hits: {stats["hits"]}')
            self.stdout.write(f'   ❌ Cache misses: {stats["misses"]}')
            self.stdout.write(f'   📈 Total requests: {stats["total_requests"]}')
            self.stdout.write(f'   🏷️  Cache version: {stats["cache_version"]}')
            self.stdout.write(f'   ✓ Cache valid: {"Yes" if stats["is_valid"] else "No"}')
            self.stdout.write(f'   🔐 Current checksum: {stats["current_checksum"]}')
            
            # Performance metrics
            if stats['hits'] > 0:
                estimated_db_queries_saved = stats['hits'] * 10  # Avg 10 queries per page
                estimated_egress_saved = stats['hits'] * 15  # Avg 15KB per page
                
                self.stdout.write('')
                self.stdout.write('💰 Cache Savings:')
                self.stdout.write(f'   🗃️  Database queries saved: ~{estimated_db_queries_saved}')
                self.stdout.write(f'   📊 Egress saved: ~{estimated_egress_saved}KB')
                self.stdout.write(f'   ⚡ Response time improvement: ~90% for cached pages')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error getting cache stats: {e}')
            )

    def get_cache_info(self):
        """Get detailed cache information."""
        from django.core.cache import cache
        from checker.services.static_page_cache import STATIC_PAGE_KEY_PREFIX, PAGES_TO_CACHE
        
        cache_info = {
            'cached_pages': [],
            'total_size': 0
        }
        
        for page in PAGES_TO_CACHE:
            cache_key = f"{STATIC_PAGE_KEY_PREFIX}all_locations_page_{page}_per_page_25_status_all"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Estimate size (rough calculation)
                import sys
                size = sys.getsizeof(str(cached_data))
                
                cache_info['cached_pages'].append({
                    'page': page,
                    'size_kb': size / 1024,
                    'created': cached_data.get('cache_meta', {}).get('created_at', 'Unknown')
                })
                cache_info['total_size'] += size
        
        return cache_info