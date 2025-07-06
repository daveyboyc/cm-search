#!/usr/bin/env python
"""Verify the fix is working correctly"""
import os
import django
import sys
import time

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def verify_fix():
    """Verify the performance fix is working"""
    print("🔍 VERIFYING PERFORMANCE FIX")
    print("=" * 50)
    
    # Test the exact scenario that was slow
    print("\n1️⃣ Testing SW11 postcode lookup (was 5.6s)...")
    
    from checker.services import get_all_postcodes_for_area
    
    start = time.time()
    postcodes = get_all_postcodes_for_area("SW11")
    elapsed = time.time() - start
    
    print(f"   Result: {postcodes}")
    print(f"   Time: {elapsed:.3f}s")
    
    if elapsed < 0.1:  # Should be under 100ms
        print("   ✅ PASS - Fast lookup working!")
    else:
        print("   ❌ FAIL - Still slow")
    
    # Test location mapping load
    print("\n2️⃣ Testing location mapping load...")
    
    from checker.services import get_location_to_postcodes_mapping
    
    start = time.time()
    mapping = get_location_to_postcodes_mapping()
    elapsed = time.time() - start
    
    print(f"   Locations: {len(mapping)}")
    print(f"   Time: {elapsed:.3f}s")
    
    if elapsed < 0.1 and len(mapping) > 10000:
        print("   ✅ PASS - Static mapping loaded!")
    else:
        print("   ❌ FAIL - Not using static files")
    
    # Test a few more locations
    print("\n3️⃣ Testing multiple location lookups...")
    
    test_cases = ["nottingham", "manchester", "bristol", "peckham"]
    total_time = 0
    
    for location in test_cases:
        start = time.time()
        result = get_all_postcodes_for_area(location)
        elapsed = time.time() - start
        total_time += elapsed
        
        status = "✅" if elapsed < 0.1 else "❌"
        print(f"   {location}: {len(result)} postcodes in {elapsed:.3f}s {status}")
    
    avg_time = total_time / len(test_cases)
    print(f"\n   Average: {avg_time:.3f}s per lookup")
    
    if avg_time < 0.05:
        print("   ✅ ALL TESTS PASSED!")
    else:
        print("   ❌ Performance not optimal")
    
    # Check static files exist
    print("\n4️⃣ Checking static files...")
    
    static_dir = os.path.join(os.path.dirname(__file__), 'capacity_checker', 'static', 'cache')
    files = ['outward_locations.json', 'location_counts.json', 'search_index.json']
    
    all_exist = True
    for filename in files:
        filepath = os.path.join(static_dir, filename)
        exists = os.path.exists(filepath)
        status = "✅" if exists else "❌"
        
        if exists:
            size = os.path.getsize(filepath) / 1024 / 1024
            print(f"   {filename}: {status} ({size:.2f} MB)")
        else:
            print(f"   {filename}: {status} NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("   ✅ All static files present!")
    else:
        print("   ❌ Missing static files")
    
    print("\n" + "=" * 50)
    print("🎯 SUMMARY: The fix is", "WORKING! 🎉" if avg_time < 0.05 and all_exist else "NOT WORKING ❌")

if __name__ == '__main__':
    verify_fix()