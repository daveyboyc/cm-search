#!/usr/bin/env python
"""Test the fast location lookup performance"""
import os
import django
import sys
import time

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def test_location_performance():
    """Test location lookup performance"""
    print("🚀 Testing location lookup performance")
    print("=" * 50)
    
    # Test the slow version first (if available)
    try:
        from checker.services.postcode_helpers import get_all_postcodes_for_area as slow_lookup
        
        print("\n📍 Testing SLOW location lookup (database)...")
        start = time.time()
        result = slow_lookup("SW11")
        elapsed = time.time() - start
        print(f"❌ SLOW: Found {len(result)} postcodes in {elapsed:.3f} seconds")
        
    except Exception as e:
        print(f"Could not test slow version: {e}")
    
    # Test the fast version
    try:
        from checker.services.postcode_helpers_fast import get_all_postcodes_for_area as fast_lookup
        
        print("\n📍 Testing FAST location lookup (static JSON)...")
        
        # First call (loads data)
        start = time.time()
        result = fast_lookup("SW11")
        elapsed = time.time() - start
        print(f"✅ FAST (first call): Found {len(result)} postcodes in {elapsed:.3f} seconds")
        
        # Second call (uses cached data)
        start = time.time()
        result = fast_lookup("SW11")
        elapsed = time.time() - start
        print(f"✅ FAST (cached): Found {len(result)} postcodes in {elapsed:.3f} seconds")
        
        # Test location search
        test_locations = ["nottingham", "peckham", "battersea", "clapham"]
        print("\n📍 Testing multiple location lookups...")
        
        total_time = 0
        for location in test_locations:
            start = time.time()
            result = fast_lookup(location)
            elapsed = time.time() - start
            total_time += elapsed
            print(f"  - {location}: {len(result)} postcodes in {elapsed:.3f}s")
        
        print(f"\n✅ Total time for {len(test_locations)} lookups: {total_time:.3f}s")
        print(f"✅ Average time per lookup: {total_time/len(test_locations):.3f}s")
        
    except Exception as e:
        print(f"❌ Error testing fast version: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_location_performance()