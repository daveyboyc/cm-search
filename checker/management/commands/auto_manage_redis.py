from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import redis
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically manage Redis memory to prevent 80% alerts'

    def handle(self, *args, **options):
        """Auto-manage Redis memory usage."""
        try:
            # Get Redis connection
            redis_url = settings.CACHES['default']['LOCATION']
            r = redis.from_url(redis_url)
            
            # Get memory info
            info = r.info('memory')
            used_memory = info['used_memory']
            redis_limit = 50 * 1024 * 1024  # 50MB
            usage_percent = (used_memory / redis_limit) * 100
            
            self.stdout.write(f"Current Redis usage: {usage_percent:.1f}%")
            
            # If usage is above 75%, start cleanup
            if usage_percent > 75:
                self.stdout.write(self.style.WARNING("Redis usage high - starting cleanup..."))
                
                # 1. Clear old map cache entries (usually the biggest)
                map_keys = r.keys('map_data*')
                if map_keys:
                    # Keep only recent map entries (last 1 hour)
                    one_hour_ago = time.time() - 3600
                    cleared = 0
                    for key in map_keys:
                        ttl = r.ttl(key)
                        # If TTL is more than 1 hour, reduce it
                        if ttl > 3600:
                            r.expire(key, 3600)
                            cleared += 1
                    self.stdout.write(f"Reduced TTL on {cleared} map cache entries")
                
                # 2. Clear search result caches older than 15 minutes
                search_patterns = ['search_*', 'count_*', ':1:location_ids:*']
                for pattern in search_patterns:
                    keys = r.keys(pattern)
                    for key in keys:
                        ttl = r.ttl(key)
                        if ttl > 900:  # 15 minutes
                            r.expire(key, 900)
                
                # 3. Company search now uses PostgreSQL - no Redis cleanup needed
                self.stdout.write("Company search uses PostgreSQL (no Redis cleanup needed)")
                
                # 4. Force expire anything with very long TTL
                all_keys = r.keys('*')
                for key in all_keys:
                    ttl = r.ttl(key)
                    if ttl > 86400:  # More than 24 hours
                        # Cap at 12 hours max
                        r.expire(key, 43200)
                        self.stdout.write(f"Capped TTL for {key.decode() if isinstance(key, bytes) else key}")
                
                # Check usage again
                info = r.info('memory')
                new_usage = (info['used_memory'] / redis_limit) * 100
                self.stdout.write(f"New Redis usage: {new_usage:.1f}%")
                
                if new_usage > 80:
                    # Emergency cleanup - delete non-critical caches
                    self.stdout.write(self.style.ERROR("Still above 80% - emergency cleanup!"))
                    
                    # Delete all map data (can be regenerated)
                    map_deleted = r.delete(*r.keys('map_data*')) if r.keys('map_data*') else 0
                    self.stdout.write(f"Deleted {map_deleted} map cache entries")
                    
                    # Delete old search caches
                    search_deleted = 0
                    for pattern in ['search_*', 'count_*']:
                        keys = r.keys(pattern)
                        if keys:
                            search_deleted += r.delete(*keys)
                    self.stdout.write(f"Deleted {search_deleted} search cache entries")
            
            else:
                self.stdout.write(self.style.SUCCESS(f"Redis usage healthy at {usage_percent:.1f}%"))
                
        except Exception as e:
            logger.error(f"Error in auto Redis management: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))