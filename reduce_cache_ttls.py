#!/usr/bin/env python
"""
Reduce cache TTLs across the codebase to prevent Redis memory spikes.
"""
import os
import re

def update_file_ttls(filepath, replacements):
    """Update TTL values in a file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        original = content
        for old, new in replacements:
            content = re.sub(old, new, content)
        
        if content != original:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✅ Updated {filepath}")
            return True
        else:
            print(f"ℹ️  No changes needed in {filepath}")
            return False
    except Exception as e:
        print(f"❌ Error updating {filepath}: {str(e)}")
        return False

def main():
    print("Reducing cache TTLs to prevent Redis memory spikes...")
    print("=" * 60)
    
    # Map cache TTLs - reduce from 2 days to 1 day
    update_file_ttls(
        'checker/services/map_cache.py',
        [
            (r'MAP_DATA_EXPIRATION = 60 \* 60 \* 24 \* 2', 'MAP_DATA_EXPIRATION = 60 * 60 * 24 * 1'),
            (r'MAP_CLUSTER_EXPIRATION = 60 \* 60 \* 24 \* 2', 'MAP_CLUSTER_EXPIRATION = 60 * 60 * 24 * 1'),
            (r'MAP_DETAIL_EXPIRATION = 60 \* 60 \* 24 \* 2', 'MAP_DETAIL_EXPIRATION = 60 * 60 * 24 * 1'),
        ]
    )
    
    # CMU dataframe cache - reduce from 7 days to 1 day
    update_file_ttls(
        'checker/services/data_access.py',
        [
            (r'CACHE_TTL = 3600 \* 24 \* 7', 'CACHE_TTL = 3600 * 24 * 1'),
        ]
    )
    
    # Statistics cache - reduce from 6 hours to 1 hour
    update_file_ttls(
        'checker/management/commands/build_statistics_cache.py',
        [
            (r'cache_timeout=21600', 'cache_timeout=3600'),  # 6 hours to 1 hour
        ]
    )
    
    # Search cache TTLs - reduce to 30 minutes
    files_with_cache_ttl = [
        'checker/views.py',
        'checker/services/company_search.py',
        'checker/services/postcode_helpers.py'
    ]
    
    for filepath in files_with_cache_ttl:
        update_file_ttls(
            filepath,
            [
                (r'CACHE_TTL = 3600', 'CACHE_TTL = 1800'),  # 1 hour to 30 minutes
                (r'cache_timeout = 3600', 'cache_timeout = 1800'),
                (r'timeout=3600', 'timeout=1800'),
            ]
        )
    
    print("\n" + "=" * 60)
    print("TTL reductions completed!")
    print("\nNext steps:")
    print("1. Run: python patch_redis_settings.py")
    print("2. Set emergency environment variables:")
    print("   heroku config:set REDIS_EMERGENCY_MODE=true DISABLE_MAP_CACHE=true")
    print("3. Deploy changes to Heroku")
    print("4. Monitor with: heroku redis:info")

if __name__ == "__main__":
    main()