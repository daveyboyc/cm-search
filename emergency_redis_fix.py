#!/usr/bin/env python3
"""
EMERGENCY Redis memory fix - Clear excessive page cache and fix TTLs
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

def emergency_redis_cleanup():
    """Emergency cleanup of Redis to fix memory issues"""
    print("🚨 EMERGENCY REDIS CLEANUP - Fixing memory issues...")
    
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
        
        # 1. Clear all Django page cache entries (the main culprit)
        print("\n1️⃣ Clearing Django page cache entries...")
        page_cache_pattern = '*views.decorators.cache*'
        page_cache_keys = r.keys(page_cache_pattern)
        if page_cache_keys:
            deleted = r.delete(*page_cache_keys)
            print(f"   ✅ Deleted {deleted} page cache entries")
        
        # 2. Fix postcode mapping TTL (currently has no expiration)
        print("\n2️⃣ Setting TTL on postcode mapping...")
        postcode_key = 'location_to_postcodes_mapping'
        if r.exists(postcode_key):
            r.expire(postcode_key, 86400)  # Set 24 hour expiration
            print(f"   ✅ Set 24-hour TTL on postcode mapping")
        
        # 3. Clear old/expired entries
        print("\n3️⃣ Clearing expired entries...")
        # Django cache cleanup
        try:
            cache.clear()
            print("   ✅ Cleared Django cache")
        except:
            print("   ⚠️  Could not clear Django cache")
        
        # 4. Get memory usage after cleanup
        info = r.info('memory')
        used_memory_mb = info['used_memory'] / 1024 / 1024
        used_memory_human = info['used_memory_human']
        maxmemory = info.get('maxmemory', 0)
        
        if maxmemory > 0:
            usage_percent = (info['used_memory'] / maxmemory) * 100
            print(f"\n📊 Redis Memory Status:")
            print(f"   • Used: {used_memory_human} ({usage_percent:.1f}% of limit)")
            print(f"   • Free: {(maxmemory - info['used_memory']) / 1024 / 1024:.1f} MB")
        else:
            print(f"\n📊 Redis Memory: {used_memory_human}")
        
        # 5. List remaining large keys
        print("\n🔍 Remaining large keys:")
        cursor = 0
        large_keys = []
        while True:
            cursor, keys = r.scan(cursor, count=100)
            for key in keys:
                try:
                    memory = r.memory_usage(key)
                    if memory and memory > 100000:  # Keys larger than 100KB
                        ttl = r.ttl(key)
                        large_keys.append((key.decode('utf-8', errors='ignore'), memory, ttl))
                except:
                    pass
            if cursor == 0:
                break
        
        # Sort by size
        large_keys.sort(key=lambda x: x[1], reverse=True)
        for key, memory, ttl in large_keys[:10]:
            ttl_str = f"{ttl}s" if ttl > 0 else "No expiration" if ttl == -1 else "Not found"
            print(f"   • {key[:50]}... - {memory/1024/1024:.2f} MB (TTL: {ttl_str})")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    
    return True


def reduce_cache_timeouts():
    """Recommendation for reducing cache timeouts in views"""
    print("\n🔧 RECOMMENDED CHANGES:")
    print("1. Edit views_technology_optimized.py:")
    print("   Change: @cache_page(60 * 10)  # 10 minutes")
    print("   To:     @cache_page(60 * 2)   # 2 minutes")
    print()
    print("2. Edit views_company_optimized.py:")
    print("   Change: @cache_page(60 * 10)  # 10 minutes")
    print("   To:     @cache_page(60 * 2)   # 2 minutes")
    print()
    print("3. Or temporarily disable page caching:")
    print("   Comment out: # @cache_page(60 * 10)")
    print()
    print("4. Add to settings.py:")
    print("   CACHE_MIDDLEWARE_SECONDS = 120  # 2 minutes max")


if __name__ == '__main__':
    success = emergency_redis_cleanup()
    if success:
        reduce_cache_timeouts()
        print("\n✅ Emergency cleanup complete!")
        print("⚠️  Deploy these changes immediately to prevent memory spikes!")
    else:
        print("\n❌ Cleanup failed - manual intervention needed")