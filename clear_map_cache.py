#!/usr/bin/env python
"""
Script to clear map cache for specific search queries
"""
import os
import django
import time
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from django.core.cache import cache

def clear_map_cache(query=None):
    """Clear map cache for a specific query or all map cache"""
    print("\n---- CLEARING MAP CACHE ----\n")
    
    # Special case for SW11
    if query and query.upper() == 'SW11':
        # Clear with current timestamp pattern
        current_time = int(time.time() / 300)  # Changes every 5 minutes
        sw11_key = f"map_data_sw11_{current_time}"
        
        # Also clear with nearby timestamps in case of clock differences
        nearby_times = [current_time-1, current_time, current_time+1]
        for t in nearby_times:
            key = f"map_data_sw11_{t}"
            print(f"Clearing SW11 cache key: {key}")
            cache.delete(key)
        
        # Also clear file-based cache
        import glob
        for cache_file in glob.glob('/Users/davidcrawford/PycharmProjects/cmr/data_cache/map_data_sw11_*.json'):
            print(f"Removing cache file: {cache_file}")
            try:
                os.remove(cache_file)
            except:
                print(f"Failed to remove {cache_file}")
    
    # Clear all map cache
    else:
        # List all keys with pattern match
        if hasattr(cache, 'keys'):
            try:
                map_keys = [k for k in cache.keys('*') if k.startswith('map_data')]
                print(f"Found {len(map_keys)} map cache keys")
                for key in map_keys:
                    print(f"Clearing cache key: {key}")
                    cache.delete(key)
            except Exception as e:
                print(f"Error listing cache keys: {e}")
        else:
            print("Cache backend doesn't support keys() method")
        
        # Also clear file-based cache
        import glob
        for cache_file in glob.glob('/Users/davidcrawford/PycharmProjects/cmr/data_cache/map_data_*.json'):
            print(f"Removing cache file: {cache_file}")
            try:
                os.remove(cache_file)
            except:
                print(f"Failed to remove {cache_file}")
    
    print("\n---- CACHE CLEARING COMPLETE ----\n")

if __name__ == "__main__":
    # Get query from command line or use SW11
    query = sys.argv[1] if len(sys.argv) > 1 else 'SW11'
    clear_map_cache(query)