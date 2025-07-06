#!/usr/bin/env python
"""Test statistics page after adding caching"""
import requests
import time

print("📊 Testing Statistics Page Performance After Fix")
print("=" * 50)

base_url = "http://localhost:8000"

# Test 1: First load (builds cache)
print("\n1️⃣ First load (building cache):")
start = time.time()
response = requests.get(f"{base_url}/statistics/")
first_load = time.time() - start

print(f"   Status: {response.status_code}")
print(f"   Time: {first_load:.3f}s")
print(f"   Size: {len(response.content)/1024:.1f} KB")

# Test 2: Second load (from cache)
print("\n2️⃣ Second load (from cache):")
start = time.time()
response = requests.get(f"{base_url}/statistics/")
cached_load = time.time() - start

print(f"   Status: {response.status_code}")
print(f"   Time: {cached_load:.3f}s")
print(f"   Size: {len(response.content)/1024:.1f} KB")

# Test 3: Different sort parameters
print("\n3️⃣ Testing different sort parameters:")
params_tests = [
    {"company_sort": "capacity", "company_order": "desc"},
    {"tech_sort": "capacity", "tech_order": "asc"},
    {"company_sort": "count", "tech_sort": "count"}  # Back to original
]

for params in params_tests:
    start = time.time()
    response = requests.get(f"{base_url}/statistics/", params=params)
    elapsed = time.time() - start
    
    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    print(f"   {param_str}: {elapsed:.3f}s")

# Summary
print("\n📊 PERFORMANCE SUMMARY:")
print(f"   First load: {first_load:.3f}s")
print(f"   Cached load: {cached_load:.3f}s")
print(f"   Improvement: {first_load/cached_load:.1f}x faster")

if cached_load < 0.1:
    print("\n✅ SUCCESS! Statistics page is now cached and fast!")
else:
    print("\n⚠️  Cache might not be working correctly")
    
print("\n💡 The statistics page will stay fast for 1 hour")
print("   after which it will rebuild the cache automatically")