"""
Redis optimization script to reduce memory usage
"""
import os
import django
import redis
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.conf import settings

# Connect to Redis
redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
r = redis.from_url(redis_url, decode_responses=True)

print("=== Redis Memory Analysis ===")

# Get memory info
info = r.info('memory')
used_memory_mb = info['used_memory'] / 1024 / 1024
max_memory_mb = 50  # Heroku free tier

print(f"Memory used: {used_memory_mb:.2f}MB / {max_memory_mb}MB ({used_memory_mb/max_memory_mb*100:.1f}%)")
print(f"Total keys: {r.dbsize()}")

# Analyze key patterns
print("\n=== Key Pattern Analysis ===")
patterns = {
    'map_data:*': 'Map cache',
    'cmu_df': 'CMU dataframe',
    'company_index': 'Company index', 
    'location_*': 'Location mappings',
    'search_cache:*': 'Search cache',
    'django_cache:*': 'Django cache'
}

total_size = 0
for pattern, description in patterns.items():
    keys = list(r.scan_iter(match=pattern))
    pattern_size = 0
    
    for key in keys[:10]:  # Sample first 10 keys
        try:
            size = r.memory_usage(key) or 0
            pattern_size += size * (len(keys) / min(10, len(keys)))  # Extrapolate
        except:
            pass
    
    size_mb = pattern_size / 1024 / 1024
    total_size += pattern_size
    print(f"{description:20} {len(keys):5} keys, ~{size_mb:6.2f}MB")

print(f"\nEstimated total: {total_size/1024/1024:.2f}MB")

# Recommendations
print("\n=== Optimization Recommendations ===")

# Check map cache
map_keys = list(r.scan_iter(match='map_data:*'))
if map_keys:
    print("\n1. Map Cache Optimization:")
    # Get TTLs
    ttls = [r.ttl(k) for k in map_keys[:5]]
    avg_ttl_hours = sum(ttls) / len(ttls) / 3600 if ttls else 0
    print(f"   - Current TTL: ~{avg_ttl_hours:.1f} hours")
    print(f"   - Recommendation: Reduce to 24-48 hours")
    
    # Check for DSR (largest dataset)
    dsr_keys = [k for k in map_keys if 'dsr' in k.lower() or '28270' in str(r.get(k))[:100]]
    if dsr_keys:
        print(f"   - Consider removing DSR map cache (very large)")

print("\n2. Add eviction policy in settings:")
print("   CACHES = {")
print("       'default': {")
print("           'OPTIONS': {")
print("               'MAX_ENTRIES': 5000,")
print("               'CULL_FREQUENCY': 3,")
print("           }")
print("       }")
print("   }")

print("\n3. Implement selective caching:")
print("   - Cache only frequently accessed technologies")
print("   - Use database for rare queries")
print("   - Implement cache warming for critical data only")

# Show largest keys
print("\n=== Largest Keys ===")
all_keys = list(r.scan_iter())
key_sizes = []
for key in all_keys[:100]:  # Sample
    try:
        size = r.memory_usage(key) or 0
        key_sizes.append((key, size))
    except:
        pass

key_sizes.sort(key=lambda x: x[1], reverse=True)
for key, size in key_sizes[:10]:
    print(f"{key[:50]:50} {size/1024/1024:6.2f}MB")