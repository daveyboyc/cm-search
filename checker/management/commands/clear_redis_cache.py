from django.core.management.base import BaseCommand
from django.core.cache import cache
import redis
import os


class Command(BaseCommand):
    help = 'Clear Redis cache and show memory usage'

    def handle(self, *args, **options):
        try:
            # Get Redis connection
            redis_url = os.environ.get('REDIS_URL')
            if not redis_url:
                self.stdout.write(self.style.ERROR('REDIS_URL not found in environment'))
                return
                
            r = redis.from_url(redis_url)
            
            # Check current usage
            info = r.info()
            keys_before = r.dbsize()
            memory_before = info.get('used_memory_human', 'N/A')
            
            self.stdout.write(f"Keys before clearing: {keys_before}")
            self.stdout.write(f"Memory usage before: {memory_before}")
            
            # Clear all cache
            r.flushdb()
            
            # Check after clearing
            info_after = r.info()
            keys_after = r.dbsize()
            memory_after = info_after.get('used_memory_human', 'N/A')
            
            self.stdout.write(self.style.SUCCESS(f"\nCache cleared successfully!"))
            self.stdout.write(f"Keys after clearing: {keys_after}")
            self.stdout.write(f"Memory usage after: {memory_after}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))