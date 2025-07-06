#!/usr/bin/env python3
"""
Redis monitoring script for safe incremental testing
"""
import os
import django
import redis
from urllib.parse import urlparse
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
from django.conf import settings
from checker.models import Component

def get_redis_stats():
    """Get detailed Redis memory usage"""
    try:
        redis_url = os.environ.get('REDIS_URL') or settings.CACHES['default']['LOCATION']
        r = redis.from_url(redis_url, decode_responses=True)
        
        info = r.info('memory')
        used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
        max_memory_mb = info.get('maxmemory', 0) / (1024 * 1024)
        peak_memory_mb = info.get('used_memory_peak', 0) / (1024 * 1024)
        
        # Calculate percentage if maxmemory is set
        if max_memory_mb > 0:
            usage_percent = (used_memory_mb / max_memory_mb) * 100
        else:
            usage_percent = 0
            
        total_keys = r.dbsize()
        
        return {
            'used_memory_mb': used_memory_mb,
            'max_memory_mb': max_memory_mb,
            'peak_memory_mb': peak_memory_mb,
            'usage_percent': usage_percent,
            'total_keys': total_keys,
            'status': 'OK' if usage_percent < 70 else 'WARNING' if usage_percent < 80 else 'CRITICAL'
        }
    except Exception as e:
        return {'error': str(e)}

def get_key_breakdown():
    """Get breakdown of Redis keys by type"""
    try:
        redis_url = os.environ.get('REDIS_URL') or settings.CACHES['default']['LOCATION']
        r = redis.from_url(redis_url, decode_responses=True)
        
        all_keys = r.keys('*')
        breakdown = {}
        total_size = 0
        
        for key in all_keys[:100]:  # Sample first 100 keys to avoid timeout
            try:
                memory_usage = r.memory_usage(key)
                if memory_usage:
                    total_size += memory_usage
                    
                    # Categorize by key pattern
                    if 'location' in key.lower():
                        breakdown['location_data'] = breakdown.get('location_data', 0) + memory_usage
                    elif 'map' in key.lower():
                        breakdown['map_data'] = breakdown.get('map_data', 0) + memory_usage
                    elif 'cmu' in key.lower():
                        breakdown['cmu_data'] = breakdown.get('cmu_data', 0) + memory_usage
                    elif 'company' in key.lower():
                        breakdown['company_data'] = breakdown.get('company_data', 0) + memory_usage
                    else:
                        breakdown['other'] = breakdown.get('other', 0) + memory_usage
            except:
                continue
                
        # Convert to MB
        for key in breakdown:
            breakdown[key] = breakdown[key] / (1024 * 1024)
            
        return breakdown, len(all_keys)
        
    except Exception as e:
        return {}, 0

def monitor_before_after(operation_name):
    """Monitor Redis before and after an operation"""
    print(f"\n{'='*60}")
    print(f"REDIS MONITORING: {operation_name}")
    print(f"{'='*60}")
    
    # Before stats
    before_stats = get_redis_stats()
    before_breakdown, before_keys = get_key_breakdown()
    
    print(f"BEFORE {operation_name}:")
    if 'error' in before_stats:
        print(f"  ❌ Error: {before_stats['error']}")
        return False
        
    print(f"  📊 Memory: {before_stats['used_memory_mb']:.1f}MB / {before_stats['max_memory_mb']:.1f}MB ({before_stats['usage_percent']:.1f}%)")
    print(f"  🔑 Keys: {before_stats['total_keys']:,}")
    print(f"  🎯 Status: {before_stats['status']}")
    
    if before_breakdown:
        print("  📂 Memory breakdown:")
        for category, size_mb in sorted(before_breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"    {category}: {size_mb:.1f}MB")
    
    # Safety check
    if before_stats['usage_percent'] > 75:
        print(f"  🚨 WARNING: Redis usage > 75%! Consider cleanup before proceeding.")
        return False
        
    return before_stats

def check_database_counts():
    """Check current database state"""
    total_components = Component.objects.count()
    distinct_cmus = Component.objects.values('cmu_id').distinct().count()
    
    print(f"\n📊 DATABASE STATUS:")
    print(f"  Components: {total_components:,}")
    print(f"  Unique CMUs: {distinct_cmus:,}")
    
    return total_components, distinct_cmus

if __name__ == "__main__":
    print("🔍 REDIS SAFETY CHECK")
    
    # Check current status
    stats = get_redis_stats()
    db_components, db_cmus = check_database_counts()
    
    if 'error' in stats:
        print(f"❌ Redis connection failed: {stats['error']}")
        exit(1)
        
    print(f"\n📊 CURRENT REDIS STATUS:")
    print(f"  Memory: {stats['used_memory_mb']:.1f}MB / {stats['max_memory_mb']:.1f}MB ({stats['usage_percent']:.1f}%)")
    print(f"  Keys: {stats['total_keys']:,}")
    print(f"  Status: {stats['status']}")
    
    # Safety recommendations
    if stats['usage_percent'] > 80:
        print(f"\n🚨 CRITICAL: Redis usage > 80%!")
        print(f"   Recommendation: Run emergency cleanup BEFORE any operations")
        print(f"   Command: python emergency_redis_cleanup.py")
    elif stats['usage_percent'] > 70:
        print(f"\n⚠️  WARNING: Redis usage > 70%")
        print(f"   Recommendation: Monitor closely, consider cleanup")
    else:
        print(f"\n✅ SAFE: Redis usage < 70%")
        print(f"   Recommendation: Proceed with small test crawl")
        
    print(f"\n🎯 SUGGESTED TEST PLAN:")
    print(f"   1. Crawl 5 CMUs: python manage.py crawl_to_database --limit 5")
    print(f"   2. Monitor Redis impact")
    print(f"   3. If safe, crawl 50 CMUs")
    print(f"   4. Build minimal caches and test")