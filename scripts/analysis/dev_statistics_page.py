#!/usr/bin/env python
"""Test statistics page performance"""
import os
import django
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.test import Client
from django.core.cache import cache
from checker.models import Component
from django.db.models import Count, Sum

print("📊 Testing Statistics Page Performance")
print("=" * 60)

# Create a test client
client = Client()

# Test 1: Time the statistics page load
print("\n1️⃣ Testing page load time:")
start = time.time()
response = client.get('/statistics/')
elapsed = time.time() - start

print(f"   Status: {response.status_code}")
print(f"   Time: {elapsed:.3f}s")
print(f"   Size: {len(response.content)/1024:.1f} KB")

if elapsed > 2:
    print("   ❌ TOO SLOW!")
else:
    print("   ✅ Good performance")

# Test 2: Check what queries are being run
print("\n2️⃣ Testing individual statistics queries:")

# Technology counts
start = time.time()
tech_counts = Component.objects.values('technology').annotate(
    count=Count('id'),
    total_capacity=Sum('derated_capacity_mw')
).order_by('-count')[:20]
list(tech_counts)  # Force evaluation
tech_time = time.time() - start
print(f"   Technology counts: {tech_time:.3f}s")

# Company counts
start = time.time()
company_counts = Component.objects.values('company_name').annotate(
    count=Count('id'),
    total_capacity=Sum('derated_capacity_mw')
).order_by('-count')[:20]
list(company_counts)  # Force evaluation
company_time = time.time() - start
print(f"   Company counts: {company_time:.3f}s")

# Location counts
start = time.time()
location_counts = Component.objects.values('location').annotate(
    count=Count('id')
).order_by('-count')[:20]
list(location_counts)  # Force evaluation
location_time = time.time() - start
print(f"   Location counts: {location_time:.3f}s")

# Year counts
start = time.time()
year_counts = Component.objects.values('delivery_year').annotate(
    count=Count('id'),
    total_capacity=Sum('derated_capacity_mw')
).order_by('delivery_year')
list(year_counts)  # Force evaluation
year_time = time.time() - start
print(f"   Year counts: {year_time:.3f}s")

# Total statistics
start = time.time()
total_components = Component.objects.count()
total_capacity = Component.objects.aggregate(Sum('derated_capacity_mw'))
total_time = time.time() - start
print(f"   Total statistics: {total_time:.3f}s")

total_query_time = tech_time + company_time + location_time + year_time + total_time
print(f"\n   Total query time: {total_query_time:.3f}s")

# Test 3: Check if statistics are cached
print("\n3️⃣ Checking cache status:")
cache_keys = [
    'statistics_technology_counts',
    'statistics_company_counts',
    'statistics_location_counts',
    'statistics_year_counts',
    'statistics_total_components',
    'statistics_total_capacity'
]

for key in cache_keys:
    cached = cache.get(key)
    if cached:
        print(f"   ✅ {key}: CACHED")
    else:
        print(f"   ❌ {key}: NOT CACHED")

# Test 4: Test with caching
print("\n4️⃣ Testing with manual caching:")

# Cache the results
cache.set('statistics_technology_counts', list(tech_counts), 3600)
cache.set('statistics_company_counts', list(company_counts), 3600)
cache.set('statistics_location_counts', list(location_counts), 3600)
cache.set('statistics_year_counts', list(year_counts), 3600)
cache.set('statistics_total_components', total_components, 3600)
cache.set('statistics_total_capacity', total_capacity, 3600)

# Load page again
start = time.time()
response = client.get('/statistics/')
cached_elapsed = time.time() - start

print(f"   First load: {elapsed:.3f}s")
print(f"   Cached load: {cached_elapsed:.3f}s")
print(f"   Improvement: {elapsed/cached_elapsed:.1f}x faster")

# Test 5: Look at the view code
print("\n5️⃣ Checking view implementation:")
try:
    from checker.views import statistics
    import inspect
    source = inspect.getsource(statistics)
    if 'cache' in source:
        print("   ✅ View uses caching")
    else:
        print("   ❌ View does NOT use caching")
        print("   💡 This is likely why it's slow!")
except:
    print("   Could not inspect view source")

print("\n💡 RECOMMENDATIONS:")
print("1. Add caching to the statistics view")
print("2. Cache results for at least 1 hour") 
print("3. Clear cache after crawls")
print("4. Consider pre-computing statistics")