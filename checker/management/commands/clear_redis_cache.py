from django.core.management.base import BaseCommand
from django.core.cache import cache
import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear Redis cache and show memory usage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=70,
            help='Clear cache if memory usage is above this percentage (default: 70)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force clear cache regardless of memory usage'
        )

    def handle(self, *args, **options):
        try:
            # Connect to Redis
            redis_url = settings.CACHES['default']['LOCATION']
            redis_client = redis.from_url(redis_url)
            
            # Check memory usage
            info = redis_client.info('memory')
            used_memory = info.get('used_memory', 0)
            
            # Heroku Redis free tier is 30MB
            max_memory = 30 * 1024 * 1024  # 30MB in bytes
            usage_percentage = (used_memory / max_memory) * 100
            
            self.stdout.write(f"Redis Memory Usage: {usage_percentage:.1f}% ({used_memory / 1024 / 1024:.1f}MB / 30MB)")
            
            # Clear if above threshold or forced
            threshold = options['threshold']
            if options['force'] or usage_percentage >= threshold:
                self.stdout.write(self.style.WARNING(f"Clearing cache (usage {usage_percentage:.1f}% >= {threshold}% threshold)..."))
                
                # Clear all cache
                cache.clear()
                
                # Check memory after clearing
                info_after = redis_client.info('memory')
                used_after = info_after.get('used_memory', 0)
                usage_after = (used_after / max_memory) * 100
                
                self.stdout.write(self.style.SUCCESS(
                    f"Cache cleared\! Memory usage: {usage_after:.1f}% ({used_after / 1024 / 1024:.1f}MB / 30MB)"
                ))
                
                freed = used_memory - used_after
                self.stdout.write(self.style.SUCCESS(f"Freed {freed / 1024 / 1024:.1f}MB of memory"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"Cache not cleared (usage {usage_percentage:.1f}% < {threshold}% threshold)"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
EOF < /dev/null