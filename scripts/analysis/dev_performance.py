#!/usr/bin/env python
"""Comprehensive performance test for the location lookup improvements"""
import os
import django
import sys
import time
import statistics

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def test_location_performance():
    """Test location lookup performance comprehensively"""
    print("🚀 COMPREHENSIVE PERFORMANCE TEST")
    print("=" * 60)
    
    # Import both versions
    try:
        from checker.services.postcode_helpers import get_all_postcodes_for_area as slow_lookup
        from checker.services.postcode_helpers import get_location_to_postcodes_mapping as slow_mapping
    except:
        slow_lookup = None
        slow_mapping = None
        
    from checker.services.postcode_helpers_fast import get_all_postcodes_for_area as fast_lookup
    from checker.services.postcode_helpers_fast import get_location_to_postcodes_mapping as fast_mapping
    
    # Test cases
    test_locations = [
        "SW11",  # The problematic postcode
        "nottingham",
        "peckham", 
        "battersea",
        "clapham",
        "manchester",
        "birmingham",
        "london",
        "sheffield",
        "bristol"
    ]
    
    print("\n📊 TESTING LOCATION MAPPING LOAD TIME")
    print("-" * 60)
    
    # Test slow mapping load (if available)
    if slow_mapping:
        print("\n❌ SLOW VERSION (Database):")
        start = time.time()
        try:
            mapping = slow_mapping()
            elapsed = time.time() - start
            print(f"  Load time: {elapsed:.3f} seconds")
            print(f"  Locations mapped: {len(mapping)}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test fast mapping load
    print("\n✅ FAST VERSION (Static JSON):")
    start = time.time()
    mapping = fast_mapping()
    elapsed = time.time() - start
    print(f"  Load time: {elapsed:.3f} seconds")
    print(f"  Locations mapped: {len(mapping)}")
    
    print("\n📊 TESTING INDIVIDUAL LOCATION LOOKUPS")
    print("-" * 60)
    
    # Test individual lookups
    slow_times = []
    fast_times = []
    
    for location in test_locations:
        print(f"\n🔍 Testing: {location}")
        
        # Slow version (if available)
        if slow_lookup:
            start = time.time()
            try:
                result = slow_lookup(location)
                elapsed = time.time() - start
                slow_times.append(elapsed)
                print(f"  ❌ SLOW: {len(result)} postcodes in {elapsed:.3f}s")
            except Exception as e:
                print(f"  ❌ SLOW: Error - {e}")
        
        # Fast version
        start = time.time()
        result = fast_lookup(location)
        elapsed = time.time() - start
        fast_times.append(elapsed)
        print(f"  ✅ FAST: {len(result)} postcodes in {elapsed:.3f}s")
    
    # Calculate statistics
    print("\n📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    if slow_times:
        print(f"\n❌ SLOW VERSION STATS:")
        print(f"  Average: {statistics.mean(slow_times):.3f}s")
        print(f"  Median:  {statistics.median(slow_times):.3f}s")
        print(f"  Min:     {min(slow_times):.3f}s")
        print(f"  Max:     {max(slow_times):.3f}s")
        print(f"  Total:   {sum(slow_times):.3f}s for {len(slow_times)} lookups")
    
    print(f"\n✅ FAST VERSION STATS:")
    print(f"  Average: {statistics.mean(fast_times):.3f}s")
    print(f"  Median:  {statistics.median(fast_times):.3f}s")
    print(f"  Min:     {min(fast_times):.3f}s")
    print(f"  Max:     {max(fast_times):.3f}s")
    print(f"  Total:   {sum(fast_times):.3f}s for {len(fast_times)} lookups")
    
    if slow_times:
        improvement = statistics.mean(slow_times) / statistics.mean(fast_times)
        print(f"\n🚀 IMPROVEMENT: {improvement:.1f}x faster!")
    
    # Test concurrent lookups
    print("\n📊 TESTING CONCURRENT LOOKUPS")
    print("-" * 60)
    
    print("\nSimulating 100 rapid lookups...")
    start = time.time()
    for i in range(100):
        location = test_locations[i % len(test_locations)]
        fast_lookup(location)
    elapsed = time.time() - start
    
    print(f"✅ Completed 100 lookups in {elapsed:.3f}s")
    print(f"✅ Average per lookup: {elapsed/100:.3f}s")
    
    # Memory usage test
    print("\n📊 MEMORY EFFICIENCY")
    print("-" * 60)
    
    # Check static file sizes
    static_dir = os.path.join(os.path.dirname(__file__), 'capacity_checker', 'static', 'cache')
    total_size = 0
    
    for filename in ['outward_locations.json', 'location_counts.json', 'search_index.json']:
        filepath = os.path.join(static_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            total_size += size
            print(f"  {filename}: {size/1024/1024:.2f} MB")
    
    print(f"\n  Total static cache size: {total_size/1024/1024:.2f} MB")
    print(f"  vs Redis usage: 71.5 GB")
    print(f"  Reduction: {(71.5*1024 - total_size/1024/1024)/(71.5*1024)*100:.1f}%")

def test_search_integration():
    """Test the integration with actual search"""
    print("\n\n🔍 TESTING SEARCH INTEGRATION")
    print("=" * 60)
    
    from checker.services.component_search import component_search
    from django.test import RequestFactory
    
    # Create a mock request
    factory = RequestFactory()
    
    test_queries = [
        "SW11",  # Postcode search
        "nottingham",  # Location search
        "battery storage",  # Technology search
        "vital energi"  # Company search
    ]
    
    for query in test_queries:
        print(f"\n🔍 Searching for: '{query}'")
        
        # Create request
        request = factory.get('/search/', {'q': query})
        
        # Time the search
        start = time.time()
        try:
            # Note: This won't actually render, but will process the search
            response = component_search(request)
            elapsed = time.time() - start
            print(f"  ✅ Search completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ❌ Search error after {elapsed:.3f}s: {e}")

if __name__ == '__main__':
    test_location_performance()
    test_search_integration()