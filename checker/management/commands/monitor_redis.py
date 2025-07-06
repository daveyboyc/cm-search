from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import redis
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Monitor Redis memory usage and cleanup if needed'

    def handle(self, *args, **options):
        """Monitor and manage Redis memory usage."""
        try:
            # Get Redis connection
            redis_url = settings.CACHES['default']['LOCATION']
            r = redis.from_url(redis_url)
            
            # Get memory info
            info = r.info('memory')
            used_memory = info['used_memory']
            used_memory_human = info['used_memory_human']
            used_memory_peak = info['used_memory_peak']
            used_memory_peak_human = info['used_memory_peak_human']
            
            # Calculate percentage (assuming 50MB limit for Heroku free Redis)
            redis_limit = 50 * 1024 * 1024  # 50MB in bytes
            usage_percent = (used_memory / redis_limit) * 100
            
            self.stdout.write(f"Redis Memory Usage: {used_memory_human} ({usage_percent:.1f}%)")
            self.stdout.write(f"Peak Memory: {used_memory_peak_human}")
            
            # List all keys and their sizes
            all_keys = r.keys('*')
            self.stdout.write(f"\nTotal keys: {len(all_keys)}")
            
            # Get size of each key
            key_sizes = []
            for key in all_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                try:
                    # Get memory usage for this key
                    size = r.memory_usage(key_str)
                    key_sizes.append((key_str, size))
                except:
                    pass
            
            # Sort by size
            key_sizes.sort(key=lambda x: x[1], reverse=True)
            
            self.stdout.write("\nTop 10 largest keys:")
            for key, size in key_sizes[:10]:
                size_mb = size / (1024 * 1024)
                self.stdout.write(f"  {key}: {size_mb:.2f} MB")
            
            # If usage is above 70%, suggest cleanup
            if usage_percent > 70:
                self.stdout.write(self.style.WARNING(f"\n⚠️  Redis usage is {usage_percent:.1f}% - cleanup recommended!"))
                
                # Check map cache specifically
                map_keys = [k for k in all_keys if b'map_data' in k or (isinstance(k, str) and 'map_data' in k)]
                if map_keys:
                    self.stdout.write(f"\nFound {len(map_keys)} map cache entries - these are often the largest")
                    
                # Check for old search cache entries
                search_keys = [k for k in all_keys if b'search_' in k or b'count_' in k or 
                              (isinstance(k, str) and ('search_' in k or 'count_' in k))]
                if search_keys:
                    self.stdout.write(f"Found {len(search_keys)} search cache entries")
                    
                self.stdout.write("\nRecommended actions:")
                self.stdout.write("1. Run: python manage.py emergency_redis_cleanup")
                self.stdout.write("2. Consider reducing cache TTLs further")
                self.stdout.write("3. Clear map cache if not critical: cache.delete_pattern('map_data*')")
            else:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Redis usage is healthy at {usage_percent:.1f}%"))
                
        except Exception as e:
            logger.error(f"Error monitoring Redis: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))