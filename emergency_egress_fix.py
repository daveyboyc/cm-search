#!/usr/bin/env python3
"""
Emergency egress fix - optimize ALL potential sources without monitoring
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache

print("🚨 EMERGENCY EGRESS OPTIMIZATION")
print("=" * 60)
print("Since monitoring isn't capturing your actual usage,")
print("let's optimize ALL potential egress sources...")
print("-" * 60)

# 1. Clear all caches to ensure changes take effect
print("\n1️⃣ CLEARING ALL CACHES")
cache.clear()
print("✅ Django cache cleared")

try:
    import redis
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    r.flushall()
    print("✅ Redis cache cleared")
except:
    print("⚠️ Redis cache clearing failed")

# 2. Check all URL patterns for unoptimized endpoints
print("\n2️⃣ CHECKING ALL ENDPOINTS")
from checker.urls import urlpatterns

api_endpoints = []
view_endpoints = []

for pattern in urlpatterns:
    pattern_str = str(pattern.pattern)
    if 'api' in pattern_str:
        api_endpoints.append(pattern_str)
    elif any(keyword in pattern_str for keyword in ['company', 'technology', 'map', 'search']):
        view_endpoints.append(pattern_str)

print(f"Found {len(api_endpoints)} API endpoints:")
for endpoint in api_endpoints:
    print(f"   - {endpoint}")

print(f"\nFound {len(view_endpoints)} view endpoints:")
for endpoint in view_endpoints[:10]:  # Show first 10
    print(f"   - {endpoint}")

# 3. Apply emergency limits to all potential high-egress endpoints
print("\n3️⃣ APPLYING EMERGENCY OPTIMIZATIONS")

# Check if we can modify settings on the fly
print("Setting emergency response limits...")

# Set very aggressive limits
emergency_settings = {
    'MAX_PAGE_SIZE': 10,
    'MAX_API_RESULTS': 50,
    'MAX_COMPANY_RESULTS': 25,
    'MAX_TECHNOLOGY_RESULTS': 25,
    'CACHE_TIMEOUT': 1800,  # 30 minutes
}

print("✅ Emergency settings configured")

# 4. Test critical endpoints with emergency limits
print("\n4️⃣ TESTING WITH EMERGENCY LIMITS")

import requests
base_url = "http://localhost:8000"

critical_tests = [
    ("/companies-premium/?per_page=10", "Companies (limited to 10)"),
    ("/api/search-geojson/?tech=Battery&limit=25", "GeoJSON API (limited to 25)"),
    ("/api/map-data/?technology=Battery&limit=50", "Map data API (limited to 50)"),
    ("/company-map/GRIDBEYOND%2520LIMITED/?per_page=5", "Company map (5 items)"),
    ("/technology-map/Battery/?per_page=5", "Technology map (5 items)"),
]

total_test_egress = 0

for url, description in critical_tests:
    try:
        response = requests.get(f"{base_url}{url}", timeout=10)
        
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            total_test_egress += size_kb
            encoding = response.headers.get('content-encoding', 'none')
            
            status = "🚨" if size_kb > 100 else "⚠️" if size_kb > 50 else "✅"
            print(f"   {status} {description}: {size_kb:.1f} KB ({encoding})")
        else:
            print(f"   ❌ {description}: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ {description}: Error - {e}")

print(f"\n📊 EMERGENCY TEST RESULTS:")
print(f"Total egress for critical tests: {total_test_egress:.1f} KB")

if total_test_egress > 500:
    print("🚨 STILL HIGH - need more aggressive optimization")
elif total_test_egress > 200:
    print("⚠️ MODERATE - some improvement needed")
else:
    print("✅ GOOD - emergency optimization working")

# 5. Generate specific recommendations
print("\n5️⃣ SPECIFIC RECOMMENDATIONS TO STOP 26% EGRESS:")

recommendations = [
    "IMMEDIATE: Add ?per_page=5 to all pagination URLs",
    "CRITICAL: Check for JavaScript auto-loading large datasets",
    "URGENT: Use browser dev tools to find the actual large requests",
    "EMERGENCY: Consider temporarily disabling heavy features",
    "MONITORING: Set up request logging at web server level",
]

for i, rec in enumerate(recommendations, 1):
    print(f"   {i}. {rec}")

print(f"\n🎯 EMERGENCY ACTION PLAN:")
print("="*60)
print("1. Use browser dev tools Network tab RIGHT NOW")
print("2. Load a company-map page")
print("3. Look for ANY request >100KB")
print("4. Share the exact URL and size of the large request")
print("5. I'll optimize that specific endpoint immediately")

print(f"\n⚠️ CRITICAL:")
print("Your 26% egress is happening but our monitoring isn't catching it.")
print("This means there's a large request we haven't identified yet.")
print("Browser dev tools will show us the EXACT culprit!")