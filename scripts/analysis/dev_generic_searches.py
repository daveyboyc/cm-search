#!/usr/bin/env python
"""Test performance for generic term searches like 'grid' and 'battery'"""
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

def test_generic_searches():
    """Test searches for generic terms that might appear in many components"""
    print("🔍 TESTING GENERIC TERM SEARCHES")
    print("=" * 60)
    
    from checker.services import get_all_postcodes_for_area
    from checker.models import Component
    from django.db.models import Q, Count
    
    # Test terms that are likely technology/description related, not locations
    test_terms = [
        "grid",
        "battery", 
        "storage",
        "energy",
        "power",
        "solar",
        "wind",
        "gas",
        "diesel",
        "generation"
    ]
    
    print("\n📊 PHASE 1: Testing postcode lookup performance")
    print("-" * 60)
    
    lookup_times = []
    for term in test_terms:
        start = time.time()
        postcodes = get_all_postcodes_for_area(term)
        elapsed = time.time() - start
        lookup_times.append(elapsed)
        
        status = "✅" if elapsed < 0.1 else "⚠️"
        print(f"{term:15} → {len(postcodes):3} postcodes in {elapsed:.3f}s {status}")
    
    avg_lookup = statistics.mean(lookup_times)
    print(f"\nAverage lookup time: {avg_lookup:.3f}s")
    
    print("\n📊 PHASE 2: Testing database query performance")
    print("-" * 60)
    
    query_times = []
    for term in test_terms:
        # Test how long it takes to search for these terms in the database
        start = time.time()
        
        # Simulate what a search would do
        count = Component.objects.filter(
            Q(technology__icontains=term) |
            Q(description__icontains=term) |
            Q(location__icontains=term) |
            Q(company_name__icontains=term)
        ).count()
        
        elapsed = time.time() - start
        query_times.append(elapsed)
        
        status = "✅" if elapsed < 0.5 else "⚠️"
        print(f"{term:15} → {count:5} components in {elapsed:.3f}s {status}")
    
    avg_query = statistics.mean(query_times)
    print(f"\nAverage query time: {avg_query:.3f}s")
    
    print("\n📊 PHASE 3: Testing specific problematic terms")
    print("-" * 60)
    
    # Test the specific terms mentioned
    specific_tests = ["grid", "battery"]
    
    for term in specific_tests:
        print(f"\n🔍 Detailed test for '{term}':")
        
        # 1. Postcode lookup
        start = time.time()
        postcodes = get_all_postcodes_for_area(term)
        postcode_time = time.time() - start
        print(f"   Postcode lookup: {len(postcodes)} results in {postcode_time:.3f}s")
        
        # 2. Check if it's being treated as a location
        from checker.services.postcode_helpers_fast import load_static_location_data
        data = load_static_location_data()
        location_to_postcodes = data.get('location_to_postcodes', {})
        
        is_location = False
        matching_locations = []
        for location, codes in location_to_postcodes.items():
            if term.lower() in location.lower():
                is_location = True
                matching_locations.append(location)
        
        if is_location:
            print(f"   ⚠️  Found in {len(matching_locations)} location names:")
            for loc in matching_locations[:5]:  # Show first 5
                print(f"      - {loc}")
            if len(matching_locations) > 5:
                print(f"      ... and {len(matching_locations) - 5} more")
        else:
            print(f"   ✅ Not treated as a location name")
        
        # 3. Component search breakdown
        print(f"\n   Component matches:")
        
        tech_count = Component.objects.filter(technology__icontains=term).count()
        desc_count = Component.objects.filter(description__icontains=term).count()
        loc_count = Component.objects.filter(location__icontains=term).count()
        company_count = Component.objects.filter(company_name__icontains=term).count()
        
        print(f"      Technology field: {tech_count}")
        print(f"      Description field: {desc_count}")
        print(f"      Location field: {loc_count}")
        print(f"      Company field: {company_count}")
        
        # 4. Sample matches
        print(f"\n   Sample technology matches:")
        techs = Component.objects.filter(
            technology__icontains=term
        ).values_list('technology', flat=True).distinct()[:5]
        
        for tech in techs:
            print(f"      - {tech}")
    
    print("\n📊 PHASE 4: Testing combined search simulation")
    print("-" * 60)
    
    # Simulate what happens when searching for these terms
    combined_test_terms = ["grid", "battery", "battery storage", "grid stability"]
    
    for search_query in combined_test_terms:
        print(f"\n🔍 Simulating search for: '{search_query}'")
        
        total_start = time.time()
        
        # Step 1: Location check (this is what was slow)
        loc_start = time.time()
        postcodes = get_all_postcodes_for_area(search_query)
        loc_time = time.time() - loc_start
        
        # Step 2: Database query
        db_start = time.time()
        results = Component.objects.filter(
            Q(technology__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(cmu_id__icontains=search_query)
        )
        
        if postcodes:
            results = results.filter(Q(outward_code__in=postcodes) | Q(location__icontains=search_query))
        
        count = results.count()
        db_time = time.time() - db_start
        
        total_time = time.time() - total_start
        
        print(f"   Location check: {loc_time:.3f}s ({len(postcodes)} postcodes)")
        print(f"   Database query: {db_time:.3f}s ({count} results)")
        print(f"   Total time: {total_time:.3f}s")
        
        if total_time < 1.0:
            print(f"   ✅ Good performance!")
        else:
            print(f"   ⚠️  Could be optimized")
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"   Average postcode lookup: {avg_lookup:.3f}s")
    print(f"   Average database query: {avg_query:.3f}s")
    print(f"   Total average: {avg_lookup + avg_query:.3f}s")
    
    if avg_lookup < 0.05 and avg_query < 0.5:
        print("\n✅ Performance is GOOD for generic searches!")
    else:
        print("\n⚠️  Performance could be improved")

if __name__ == '__main__':
    test_generic_searches()