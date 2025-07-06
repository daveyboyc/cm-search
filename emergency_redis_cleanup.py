#!/usr/bin/env python3
"""
Emergency Redis cleanup script to prevent memory spikes above 80%
Removes duplicate and old cache entries, optimizes TTLs
"""
import os
import django
import sys
import redis
from urllib.parse import urlparse

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
from django.conf import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_redis():
    """Emergency Redis cleanup to prevent 80%+ usage spikes"""
    
    print("🚨 EMERGENCY REDIS CLEANUP")
    print("=" * 60)
    
    # Connect to Redis directly
    redis_url = os.environ.get('REDIS_URL') or settings.CACHES['default']['LOCATION']
    if not redis_url:
        print("❌ No Redis URL found")
        return False
    
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Get current stats
        info = r.info('memory')
        used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
        peak_memory_mb = info.get('used_memory_peak', 0) / (1024 * 1024)
        
        print(f"📊 Current Redis Status:")
        print(f"   Memory Used: {used_memory_mb:.2f} MB")
        print(f"   Peak Memory: {peak_memory_mb:.2f} MB")
        print(f"   Total Keys: {r.dbsize()}")
        
        # 1. Remove duplicate CMU dataframes (keep only v2)
        print("\n🗑️ Removing duplicate CMU dataframes...")
        patterns_to_clean = [
            ':1:cmu_dataframe_v1*',  # Remove old version
            'cmu_dataframe_v1*',     # Alternative pattern
        ]
        
        deleted_count = 0
        for pattern in patterns_to_clean:
            keys = list(r.scan_iter(match=pattern))
            for key in keys:
                r.delete(key)
                deleted_count += 1
                print(f"   Deleted: {key}")
        
        # 2. Remove old map cache entries (keep only recent)
        print(f"\n🗺️ Cleaning old map cache entries...")
        map_keys = list(r.scan_iter(match='map_data:*'))
        if len(map_keys) > 10:  # Keep only 10 most recent
            print(f"   Found {len(map_keys)} map cache entries, removing oldest...")
            # Get creation times and remove oldest
            key_times = []
            for key in map_keys:
                ttl = r.ttl(key)
                if ttl > 0:
                    key_times.append((key, ttl))
            
            # Sort by TTL (oldest have lowest TTL)
            key_times.sort(key=lambda x: x[1])
            keys_to_remove = key_times[:-10]  # Remove all but 10 newest
            
            for key, _ in keys_to_remove:
                r.delete(key)
                deleted_count += 1
                print(f"   Deleted old map cache: {key[:50]}...")
        
        # 3. Remove old search caches
        print(f"\n🔍 Cleaning search cache entries...")
        search_patterns = [
            'search_results:*',
            'search_cache:*',
            'component_detail_*',
            'views.decorators.*'
        ]
        
        for pattern in search_patterns:
            keys = list(r.scan_iter(match=pattern))
            for key in keys:
                r.delete(key)
                deleted_count += 1
        
        # 4. Set shorter TTLs on remaining keys
        print(f"\n⏰ Optimizing TTLs for remaining keys...")
        all_keys = list(r.scan_iter())
        optimized_count = 0
        
        for key in all_keys:
            current_ttl = r.ttl(key)
            
            # Set appropriate TTLs based on key type
            if 'cmu_dataframe' in key:
                new_ttl = 3600 * 24 * 3  # 3 days
            elif 'map_data' in key:
                new_ttl = 3600 * 24 * 1  # 1 day
            elif 'company' in key:
                new_ttl = 3600 * 12      # 12 hours
            else:
                new_ttl = 3600 * 6       # 6 hours default
            
            # Only update if current TTL is longer or infinite
            if current_ttl == -1 or current_ttl > new_ttl:
                r.expire(key, new_ttl)
                optimized_count += 1
        
        # Final stats
        new_info = r.info('memory')
        new_memory_mb = new_info.get('used_memory', 0) / (1024 * 1024)
        new_key_count = r.dbsize()
        
        print(f"\n✅ Cleanup completed!")
        print(f"   Keys deleted: {deleted_count}")
        print(f"   TTLs optimized: {optimized_count}")
        print(f"   Memory before: {used_memory_mb:.2f} MB")
        print(f"   Memory after:  {new_memory_mb:.2f} MB")
        print(f"   Memory saved:  {used_memory_mb - new_memory_mb:.2f} MB")
        print(f"   Keys remaining: {new_key_count}")
        
        # Calculate percentage if we have a memory limit
        max_memory_mb = 50  # Typical Heroku Redis limit
        memory_percent = (new_memory_mb / max_memory_mb) * 100
        
        print(f"\n📈 Final Status:")
        print(f"   Memory usage: {memory_percent:.1f}% of {max_memory_mb}MB limit")
        
        if memory_percent > 70:
            print("⚠️  WARNING: Still above 70% - consider emergency mode")
            print("   Run: heroku config:set REDIS_EMERGENCY_MODE=true DISABLE_MAP_CACHE=true")
        else:
            print("✅ Memory usage is now under control")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

def enable_emergency_mode():
    """Enable emergency Redis settings"""
    print("\n🚨 ENABLING EMERGENCY MODE")
    print("Add these environment variables:")
    print("   REDIS_EMERGENCY_MODE=true")
    print("   DISABLE_MAP_CACHE=true")
    print("   USE_MINIMAL_CACHE=true")
    
    print("\nFor Heroku deployment:")
    print("   heroku config:set REDIS_EMERGENCY_MODE=true \\")
    print("                     DISABLE_MAP_CACHE=true \\")
    print("                     USE_MINIMAL_CACHE=true")

if __name__ == "__main__":
    success = cleanup_redis()
    
    if not success:
        print("\n🆘 Cleanup failed - enabling emergency mode")
        enable_emergency_mode()
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Monitor Redis with: python manage.py check_redis_usage")
    print("2. Deploy optimized settings to production")
    print("3. Set up regular cleanup: schedule this script weekly")
    print("4. Consider alternative caching for map data if issues persist") 