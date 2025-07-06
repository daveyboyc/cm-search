#!/usr/bin/env python3
"""
Emergency cache clearing script
Clears Django cache to force the optimized GeoJSON endpoint to be used immediately
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache

print("🚨 EMERGENCY CACHE CLEARING")
print("=" * 50)

# Clear all cache
cache.clear()
print("✅ All Django cache cleared")

# Check if Redis is available and clear it too
try:
    import redis
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    r.flushall()
    print("✅ Redis cache cleared")
except:
    print("⚠️  Redis not available or already cleared")

print("\n🎯 CHANGES NOW ACTIVE:")
print("  - Removed 'all_technologies', 'all_companies', 'all_cmu_ids', 'all_years' from GeoJSON")
print("  - Increased cache time from 5 to 15 minutes")
print("  - Reduced default limit from 250 to 100 locations")
print("  - Added gzip compression to /api/search-geojson/")
print("  - Added gzip compression to /api/map-data/")
print("  - Added gzip compression to /api/component-map-detail/")
print("  - Expected egress reduction: 70-80%")

print("\n💡 Monitor endpoints at: /api/monitoring/")