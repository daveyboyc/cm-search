"""
Emergency cache cleanup to reduce Redis memory usage when over 90%
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
import redis
from django.conf import settings
from urllib.parse import urlparse
import time

class Command(BaseCommand):
    help = 'Emergency cache cleanup to reduce Redis memory usage'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup even if not at 90% usage',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually doing it',
        )

    def handle(self, *args, **options):
        # Get Redis connection
        redis_url = settings.CACHES['default']['LOCATION']
        parsed = urlparse(redis_url)
        r = redis.Redis(
            host=parsed.hostname,
            port=parsed.port,
            password=parsed.password,
            decode_responses=True
        )

        # Check current memory usage
        memory = r.info('memory')
        used_memory = memory.get('used_memory', 0)
        max_memory = memory.get('maxmemory', 0)
        
        if max_memory > 0:
            usage_percent = (used_memory / max_memory) * 100
            self.stdout.write(f"Current Redis usage: {usage_percent:.1f}%")
            
            if usage_percent < 90 and not options['force']:
                self.stdout.write(self.style.SUCCESS("Memory usage below 90%, no cleanup needed"))
                return
        else:
            self.stdout.write("Unable to determine max memory, proceeding with cleanup")

        self.stdout.write(self.style.WARNING("Starting emergency cache cleanup..."))
        
        # Priority cleanup order (least important first)
        cleanup_patterns = [
            # 1. Old GeoJSON cache (shortest TTL, most numerous)
            ('geojson_static:*', 'GeoJSON cache entries'),
            # 2. Map data cache (medium importance)
            ('map_data_*', 'Map data cache'),
            # 3. Map cluster cache 
            ('map_cluster:*', 'Map cluster cache'),
            # 4. Django page cache
            ('views.decorators.cache.*', 'Django page cache'),
            # 5. Statistics cache (can be rebuilt)
            ('statistics_*', 'Statistics cache'),
        ]
        
        total_deleted = 0
        
        for pattern, description in cleanup_patterns:
            self.stdout.write(f"\nCleaning {description}...")
            
            try:
                # Get keys matching pattern
                keys = []
                cursor = 0
                while True:
                    cursor, batch_keys = r.scan(cursor, match=pattern, count=100)
                    keys.extend(batch_keys)
                    if cursor == 0:
                        break
                
                if keys:
                    self.stdout.write(f"Found {len(keys)} keys matching {pattern}")
                    
                    if not options['dry_run']:
                        # Delete in batches
                        batch_size = 100
                        for i in range(0, len(keys), batch_size):
                            batch = keys[i:i + batch_size]
                            deleted = r.delete(*batch)
                            total_deleted += deleted
                            self.stdout.write(f"  Deleted batch of {deleted} keys")
                    else:
                        self.stdout.write(f"  Would delete {len(keys)} keys")
                        total_deleted += len(keys)
                else:
                    self.stdout.write(f"No keys found for pattern: {pattern}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error cleaning {pattern}: {e}"))
            
            # Check if we've freed enough memory
            if not options['dry_run']:
                memory = r.info('memory')
                used_memory = memory.get('used_memory', 0)
                if max_memory > 0:
                    new_usage = (used_memory / max_memory) * 100
                    self.stdout.write(f"Memory usage now: {new_usage:.1f}%")
                    if new_usage < 80:  # Stop if we're below 80%
                        self.stdout.write(self.style.SUCCESS("Memory usage reduced sufficiently"))
                        break

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would have deleted {total_deleted} cache entries"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Emergency cleanup complete: {total_deleted} entries deleted"))
            
            # Final memory report
            memory = r.info('memory')
            used_memory = memory.get('used_memory', 0)
            if max_memory > 0:
                final_usage = (used_memory / max_memory) * 100
                self.stdout.write(f"Final memory usage: {final_usage:.1f}%")