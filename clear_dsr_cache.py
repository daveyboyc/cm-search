#!/usr/bin/env python3
"""
Emergency script to clear DSR cache entries from Redis to free memory and eliminate 32s delay
"""
import os
import django
import redis
from urllib.parse import urlparse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
from django.conf import settings

def clear_dsr_cache():
    """Clear all DSR-related cache entries from Redis"""
    print("🗑️  Clearing DSR cache entries to eliminate 32-second delay...")
    
    # Get Redis connection
    redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
    parsed = urlparse(redis_url)
    
    try:
        r = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=parsed.password,
            db=0
        )
        
        # Find all DSR-related keys
        dsr_patterns = [
            '*DSR*',
            '*dsr*',
            '*technology:DSR*',
            '*tech_DSR*',
            '*map_DSR*',
            '*location_DSR*'
        ]
        
        total_freed = 0
        total_keys = 0
        
        for pattern in dsr_patterns:
            keys = r.keys(pattern)
            if keys:
                print(f"  Found {len(keys)} keys matching pattern: {pattern}")
                
                # Get memory usage before deletion
                memory_before = 0
                for key in keys:
                    try:
                        memory_before += r.memory_usage(key) or 0
                    except:
                        pass
                
                # Delete the keys
                deleted = r.delete(*keys)
                total_keys += deleted
                total_freed += memory_before
                
                print(f"  Deleted {deleted} keys, freed ~{memory_before / 1024 / 1024:.2f} MB")
        
        # Also clear Django cache entries for DSR
        dsr_cache_keys = [
            'technology_search_DSR',
            'technology_detail_DSR', 
            'technology_locations_DSR',
            'map_data_DSR',
            'company_technology_DSR'
        ]
        
        for key in dsr_cache_keys:
            try:
                cache.delete(key)
                print(f"  Cleared Django cache key: {key}")
            except:
                pass
        
        print(f"\n✅ DSR cache cleanup complete:")
        print(f"   • Total keys deleted: {total_keys}")
        print(f"   • Memory freed: ~{total_freed / 1024 / 1024:.2f} MB")
        print(f"   • Expected performance improvement: Eliminates 32-second map cache delay")
        
        # Check current Redis memory usage
        info = r.info('memory')
        used_memory_mb = info['used_memory'] / 1024 / 1024
        print(f"   • Current Redis memory usage: {used_memory_mb:.2f} MB")
        
    except Exception as e:
        print(f"❌ Error clearing DSR cache: {e}")
        print("   This is expected if Redis is not available locally")

if __name__ == '__main__':
    clear_dsr_cache()