#!/usr/bin/env python3
"""
Test script to identify egress patterns during normal app usage.
Run this to understand what operations cause high database egress.
"""
import os
import sys
import django
import time
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
from checker.models import LocationGroup, Component

def test_redis_cache():
    """Test if Redis cache is working at all."""
    print("🔧 Testing Redis Cache...")
    
    # Test basic cache operations
    test_key = "egress_test_key"
    test_value = "test_data_123"
    
    try:
        cache.set(test_key, test_value, 300)  # 5 minutes
        retrieved = cache.get(test_key)
        
        if retrieved == test_value:
            print("✅ Redis cache is working")
        else:
            print("❌ Redis cache NOT working - retrieved:", retrieved)
    except Exception as e:
        print(f"❌ Redis cache ERROR: {e}")
    
    # Check cache stats
    try:
        cache_keys = cache.keys("*")
        print(f"📊 Cache contains {len(cache_keys)} keys")
        
        # Show some cache keys
        for i, key in enumerate(cache_keys[:10]):
            print(f"   {i+1}. {key}")
        if len(cache_keys) > 10:
            print(f"   ... and {len(cache_keys) - 10} more")
            
    except Exception as e:
        print(f"⚠️  Cannot inspect cache keys: {e}")

def test_search_operations():
    """Test common search operations that might cause egress."""
    print("\n🔍 Testing Search Operations...")
    
    search_terms = ['battery', 'grid', 'manchester', 'asda']
    
    for term in search_terms:
        print(f"\n--- Testing search: '{term}' ---")
        start_time = time.time()
        
        # Test LocationGroup search (optimized path)
        try:
            lg_count = LocationGroup.objects.filter(
                location__icontains=term
            ).count()
            lg_time = time.time() - start_time
            print(f"✅ LocationGroup search: {lg_count} results in {lg_time:.3f}s")
        except Exception as e:
            print(f"❌ LocationGroup search failed: {e}")
        
        # Test Component search (legacy path)
        try:
            start_time = time.time()
            comp_count = Component.objects.filter(
                location__icontains=term
            ).count()
            comp_time = time.time() - start_time
            print(f"⚠️  Component search: {comp_count} results in {comp_time:.3f}s")
        except Exception as e:
            print(f"❌ Component search failed: {e}")

def test_map_operations():
    """Test map-related operations."""
    print("\n🗺️  Testing Map Operations...")
    
    # Test geocoded component count
    try:
        start_time = time.time()
        geocoded_count = Component.objects.filter(
            geocoded=True,
            latitude__isnull=False,
            longitude__isnull=False
        ).count()
        elapsed = time.time() - start_time
        print(f"📍 Geocoded components: {geocoded_count} in {elapsed:.3f}s")
    except Exception as e:
        print(f"❌ Geocoded query failed: {e}")
    
    # Test technology filtering
    try:
        start_time = time.time()
        battery_count = Component.objects.filter(
            technology__icontains='battery',
            geocoded=True
        ).count()
        elapsed = time.time() - start_time
        print(f"🔋 Battery components: {battery_count} in {elapsed:.3f}s")
    except Exception as e:
        print(f"❌ Technology query failed: {e}")

def test_app_endpoints():
    """Test actual app endpoints to see response sizes."""
    print("\n🌐 Testing App Endpoints...")
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/",
        "/?q=battery",
        "/?q=manchester",
        "/search-map/?q=grid",
        "/api/map-data/?technology=Battery",
        "/statistics/",
    ]
    
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            elapsed = time.time() - start_time
            
            size_kb = len(response.content) / 1024
            status = "✅" if response.status_code == 200 else "❌"
            
            print(f"{status} {endpoint}: {response.status_code} - {size_kb:.1f}KB in {elapsed:.3f}s")
            
        except Exception as e:
            print(f"❌ {endpoint}: Failed - {e}")

def main():
    print("🚨 EGRESS PATTERN TESTING STARTED")
    print("=" * 50)
    print(f"Time: {datetime.now()}")
    print("Purpose: Identify what operations cause high database egress")
    print()
    
    test_redis_cache()
    test_search_operations() 
    test_map_operations()
    test_app_endpoints()
    
    print("\n" + "=" * 50)
    print("🏁 EGRESS TESTING COMPLETED")
    print()
    print("Next steps:")
    print("1. Check Supabase dashboard during/after this test")
    print("2. Note any egress spikes")
    print("3. Identify which operations correlate with high egress")

if __name__ == "__main__":
    main()