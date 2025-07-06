#!/usr/bin/env python
"""
Fix Redis memory spikes by implementing immediate optimizations.

This script addresses the Redis usage spiking to 98% before dropping to 80%.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
import redis
from django.conf import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_redis_memory():
    """Check current Redis memory usage."""
    try:
        redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
        info = redis_client.info('memory')
        used_memory = info.get('used_memory', 0)
        used_memory_mb = used_memory / (1024 * 1024)
        
        # Get maxmemory if set
        config = redis_client.config_get('maxmemory')
        max_memory = int(config.get('maxmemory', 0))
        
        if max_memory > 0:
            max_memory_mb = max_memory / (1024 * 1024)
            usage_percent = (used_memory / max_memory) * 100
            logger.info(f"Redis Memory: {used_memory_mb:.2f}MB / {max_memory_mb:.2f}MB ({usage_percent:.1f}%)")
        else:
            logger.info(f"Redis Memory Used: {used_memory_mb:.2f}MB (no maxmemory limit set)")
            
        return used_memory_mb
    except Exception as e:
        logger.error(f"Error checking Redis memory: {str(e)}")
        return 0


def clear_large_caches():
    """Clear the largest cache entries to free up memory."""
    logger.info("Clearing large cache entries...")
    
    # Clear map cache entries (biggest consumer)
    cleared_count = 0
    try:
        redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
        
        # Clear all map-related caches
        for key_pattern in ['map_data:*', 'map_cluster:*', 'map_detail:*']:
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=key_pattern, count=100)
                if keys:
                    redis_client.delete(*keys)
                    cleared_count += len(keys)
                if cursor == 0:
                    break
        
        logger.info(f"Cleared {cleared_count} map cache entries")
        
        # Also clear the CMU dataframe if memory is still high
        memory_mb = check_redis_memory()
        if memory_mb > 200:  # If still using more than 200MB
            cache.delete('cmu_dataframe_v1')
            logger.info("Cleared CMU dataframe cache")
            
    except Exception as e:
        logger.error(f"Error clearing caches: {str(e)}")


def set_cache_ttls():
    """Update cache TTLs to more reasonable values."""
    logger.info("Updating cache TTLs...")
    
    # These would need to be set in the actual code files
    recommendations = {
        'map_data': '24 hours (from 48 hours)',
        'cmu_dataframe': '24 hours (from 7 days)',
        'statistics': '1 hour (from 6 hours)',
        'company_search': '30 minutes (from 1 hour)'
    }
    
    for cache_type, recommendation in recommendations.items():
        logger.info(f"  - {cache_type}: {recommendation}")


def implement_emergency_measures():
    """Implement emergency measures to reduce Redis load."""
    logger.info("\nEmergency measures to implement:")
    logger.info("1. Set environment variable: REDIS_EMERGENCY_MODE=true")
    logger.info("2. Set environment variable: DISABLE_MAP_CACHE=true")
    logger.info("3. Run on Heroku: heroku config:set REDIS_EMERGENCY_MODE=true DISABLE_MAP_CACHE=true")
    logger.info("\nThis will:")
    logger.info("  - Skip startup cache validation (reduces dyno restart load)")
    logger.info("  - Disable map caching temporarily")
    logger.info("  - Reduce Redis traffic significantly")


def analyze_cache_sizes():
    """Analyze the size of different cache entries."""
    logger.info("\nAnalyzing cache entry sizes...")
    
    try:
        redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
        
        # Sample different cache types
        cache_patterns = {
            'map_data:*': 'Map Data',
            'map_cluster:*': 'Map Clusters',
            'map_detail:*': 'Map Details',
            'company_*': 'Company Data',
            'technology_*': 'Technology Data',
            'search_*': 'Search Results',
            'statistics_*': 'Statistics',
        }
        
        for pattern, name in cache_patterns.items():
            cursor = 0
            total_size = 0
            count = 0
            
            # Sample first 10 keys of each type
            cursor, keys = redis_client.scan(cursor, match=pattern, count=10)
            for key in keys:
                try:
                    size = redis_client.memory_usage(key)
                    if size:
                        total_size += size
                        count += 1
                except:
                    pass
            
            if count > 0:
                avg_size_kb = (total_size / count) / 1024
                logger.info(f"  {name}: avg {avg_size_kb:.1f}KB per entry")
                
    except Exception as e:
        logger.error(f"Error analyzing cache sizes: {str(e)}")


def main():
    logger.info("Redis Memory Spike Fix Script")
    logger.info("=" * 50)
    
    # Check current memory usage
    logger.info("\nCurrent Redis Status:")
    check_redis_memory()
    
    # Analyze cache sizes
    analyze_cache_sizes()
    
    # Clear large caches if needed
    response = input("\nClear large cache entries? (y/n): ")
    if response.lower() == 'y':
        clear_large_caches()
        logger.info("\nMemory after clearing:")
        check_redis_memory()
    
    # Show TTL recommendations
    logger.info("\nRecommended TTL changes:")
    set_cache_ttls()
    
    # Show emergency measures
    implement_emergency_measures()
    
    logger.info("\n" + "=" * 50)
    logger.info("Additional recommendations:")
    logger.info("1. Update capacity_checker/settings.py to add Redis eviction policy:")
    logger.info("   'OPTIONS': {")
    logger.info("       'MAX_ENTRIES': 5000,")
    logger.info("       'CULL_FREQUENCY': 3,")
    logger.info("   }")
    logger.info("2. Consider implementing msgpack compression for large data")
    logger.info("3. Monitor with: heroku redis:info -a your-app-name")


if __name__ == "__main__":
    main()