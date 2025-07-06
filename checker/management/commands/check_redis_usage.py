from django.core.management.base import BaseCommand
import redis
from django.conf import settings
from urllib.parse import urlparse
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Check Redis usage statistics'

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

        # Get stats
        info = r.info()
        stats = r.info('stats')
        memory = r.info('memory')
        
        self.stdout.write(self.style.SUCCESS("=== REDIS USAGE REPORT ===\n"))
        
        # Memory stats
        self.stdout.write(self.style.WARNING("MEMORY:"))
        self.stdout.write(f"  Used: {memory.get('used_memory_human', 'N/A')}")
        self.stdout.write(f"  Peak: {memory.get('used_memory_peak_human', 'N/A')}")
        self.stdout.write(f"  RSS: {memory.get('used_memory_rss_human', 'N/A')}")
        
        # Network stats
        net_in = stats.get('total_net_input_bytes', 0) / (1024**3)
        net_out = stats.get('total_net_output_bytes', 0) / (1024**3)
        net_total = net_in + net_out
        
        self.stdout.write(self.style.WARNING("\nNETWORK:"))
        self.stdout.write(f"  Input: {net_in:.2f} GB")
        self.stdout.write(f"  Output: {net_out:.2f} GB")
        self.stdout.write(self.style.ERROR(f"  Total: {net_total:.2f} GB"))
        
        # On 5GB plan, show percentage
        if net_total > 5:
            percentage = (net_total / 5) * 100
            self.stdout.write(self.style.ERROR(f"  Usage: {percentage:.0f}% of 5GB limit"))
        
        # General stats
        self.stdout.write(self.style.WARNING("\nSTATS:"))
        self.stdout.write(f"  Keys: {r.dbsize()}")
        self.stdout.write(f"  Commands: {stats.get('total_commands_processed', 0):,}")
        self.stdout.write(f"  Clients: {info.get('connected_clients', 0)}")
        
        # Check key patterns
        self.stdout.write(self.style.WARNING("\nKEY PATTERNS:"))
        patterns = {}
        cursor = 0
        for _ in range(5):  # Sample 5 batches
            cursor, keys = r.scan(cursor, count=100)
            for key in keys:
                prefix = key.split(':')[0] if ':' in key else key
                patterns[prefix] = patterns.get(prefix, 0) + 1
            if cursor == 0:
                break
        
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
            self.stdout.write(f"  {pattern}: {count} keys")
        
        # Check for large keys
        self.stdout.write(self.style.WARNING("\nLARGEST KEYS:"))
        large_keys = []
        cursor = 0
        for _ in range(10):
            cursor, keys = r.scan(cursor, count=50)
            for key in keys:
                try:
                    size = r.memory_usage(key) or 0
                    if size > 100000:  # Keys larger than 100KB
                        large_keys.append((key, size))
                except:
                    pass
            if cursor == 0:
                break
        
        for key, size in sorted(large_keys, key=lambda x: x[1], reverse=True)[:10]:
            self.stdout.write(f"  {key[:60]}...: {size / (1024**2):.2f} MB")