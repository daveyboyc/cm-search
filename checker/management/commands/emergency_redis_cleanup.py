"""
Emergency Redis cleanup - remove non-essential data to free up space
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import redis
import os

class Command(BaseCommand):
    help = 'Emergency Redis cleanup to free up space'

    def handle(self, *args, **options):
        self.stdout.write("🚨 EMERGENCY REDIS CLEANUP")
        
        # Connect to Redis directly
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            self.stdout.write(self.style.ERROR("No REDIS_URL found"))
            return
            
        r = redis.from_url(redis_url)
        
        # Get current memory usage
        info = r.info('memory')
        used_memory = info.get('used_memory_human', 'Unknown')
        self.stdout.write(f"Current Redis memory usage: {used_memory}")
        
        # Patterns to delete (non-essential caches)
        patterns_to_delete = [
            'map_data:*',           # Map cache
            'component_detail_*',   # Component details
            'search_results:*',     # Search results
            'views.decorators.*',   # Django view cache
            ':1:component_*',       # Old component cache
            ':1:technology_*',      # Old technology cache
            'company_links:*',      # Company links
            'location_groups:*',    # Location groups
        ]
        
        # Count keys before deletion
        total_keys = r.dbsize()
        self.stdout.write(f"Total keys before cleanup: {total_keys}")
        
        # Delete non-essential keys
        deleted_count = 0
        for pattern in patterns_to_delete:
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor, match=pattern, count=1000)
                if keys:
                    deleted_count += len(keys)
                    r.delete(*keys)
                    self.stdout.write(f"  Deleted {len(keys)} keys matching {pattern}")
                if cursor == 0:
                    break
        
        # Clear Django cache
        try:
            cache.clear()
            self.stdout.write("✓ Cleared Django cache")
        except Exception as e:
            self.stdout.write(f"  Error clearing Django cache: {e}")
        
        # Final stats
        remaining_keys = r.dbsize()
        info_after = r.info('memory')
        used_memory_after = info_after.get('used_memory_human', 'Unknown')
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ CLEANUP COMPLETE"))
        self.stdout.write(f"  Deleted {deleted_count} keys")
        self.stdout.write(f"  Remaining keys: {remaining_keys}")
        self.stdout.write(f"  Memory usage: {used_memory} → {used_memory_after}")
        
        # Suggest keeping only essential data
        self.stdout.write(self.style.WARNING("\n⚠️  RECOMMENDATIONS:"))
        self.stdout.write("  1. Keep only: CMU data, company index, location mapping")
        self.stdout.write("  2. Use static JSON files for technology/company lists")
        self.stdout.write("  3. Implement 15-minute TTL for all caches")
        self.stdout.write("  4. Use client-side caching for map data")