import os
import django
import time
import re

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q

def test_location_search(search_term, limit=100):
    """
    Test search functionality comparing traditional search vs. enhanced search with county/outward_code
    """
    print(f"\n=== Testing search for '{search_term}' ===\n")
    
    # Start timing
    start_time = time.time()
    
    # Traditional search (only using location field)
    traditional_filter = Q(location__icontains=search_term)
    traditional_results = Component.objects.filter(traditional_filter).distinct()
    
    traditional_time = time.time() - start_time
    traditional_count = traditional_results.count()
    
    print(f"Traditional search found {traditional_count} results in {traditional_time:.3f} seconds")
    
    # Start timing for enhanced search
    start_time = time.time()
    
    # Map location names to common outward codes
    location_to_outcode = {
        "PECKHAM": "SE15",
        "NOTTINGHAM": "NG",
        "MANCHESTER": "M",
        "LONDON": None  # Too many outward codes to list for London
    }
    
    outcode = None
    if search_term.upper() in location_to_outcode:
        outcode = location_to_outcode.get(search_term.upper())
    
    # Enhanced search (using location, county, and outward_code)
    enhanced_filter = traditional_filter
    
    if outcode:
        # Add outward code filter
        enhanced_filter |= Q(outward_code__istartswith=outcode)
    
    # Add county filter
    enhanced_filter |= Q(county__icontains=search_term)
    
    enhanced_results = Component.objects.filter(enhanced_filter).distinct()
    
    enhanced_time = time.time() - start_time
    enhanced_count = enhanced_results.count()
    
    print(f"Enhanced search found {enhanced_count} results in {enhanced_time:.3f} seconds")
    additional_count = enhanced_count - traditional_count
    print(f"Additional results found: {additional_count}")
    
    # Specifically check for outward code matches
    if outcode:
        outcode_filter = Q(outward_code__istartswith=outcode)
        
        # Exclude those that already have the location name to avoid double counting
        outcode_filter &= ~Q(location__icontains=search_term)
        
        outcode_results = Component.objects.filter(outcode_filter).distinct()
        outcode_count = outcode_results.count()
        
        print(f"\nFound {outcode_count} additional components with outward code '{outcode}' that don't mention '{search_term}'")
        
        # Show sample results from outcode matches
        print(f"\n--- Components with outward code '{outcode}' but no '{search_term}' in location ---")
        for i, result in enumerate(outcode_results[:5]):
            print(f"{i+1}. {result.location} (ID: {result.id})")
            if hasattr(result, 'county') and result.county:
                print(f"   County: {result.county}")
            if hasattr(result, 'outward_code') and result.outward_code:
                print(f"   Outward code: {result.outward_code}")
    
    # Show sample of traditional results
    print("\n--- Traditional Search Results Sample ---")
    for i, result in enumerate(traditional_results[:5]):
        print(f"{i+1}. {result.location} (ID: {result.id})")
        if hasattr(result, 'county') and result.county:
            print(f"   County: {result.county}")
        if hasattr(result, 'outward_code') and result.outward_code:
            print(f"   Outward code: {result.outward_code}")
    
    # Get the additional results not found in traditional search
    # This is a more accurate way to determine truly new results
    additional_ids = set(enhanced_results.values_list('id', flat=True)) - set(traditional_results.values_list('id', flat=True))
    
    # Now query for just these additional results
    additional_results = Component.objects.filter(id__in=additional_ids)
    true_additional_count = additional_results.count()
    
    print(f"\n--- Enhanced Search Added {true_additional_count} Unique Results ---")
    for i, result in enumerate(additional_results[:5]):
        print(f"{i+1}. {result.location} (ID: {result.id})")
        if hasattr(result, 'county') and result.county:
            print(f"   County: {result.county}")
        if hasattr(result, 'outward_code') and result.outward_code:
            print(f"   Outward code: {result.outward_code}")
    
    return {
        "traditional_count": traditional_count,
        "enhanced_count": enhanced_count,
        "additional_count": true_additional_count,
        "traditional_time": traditional_time,
        "enhanced_time": enhanced_time
    }

if __name__ == "__main__":
    # Test locations
    locations_to_test = ["peckham", "nottingham", "manchester", "london"]
    
    all_results = {}
    
    for location in locations_to_test:
        all_results[location] = test_location_search(location)
    
    # Summary of all tests
    print("\n=== Summary of Search Tests ===")
    print(f"{'Location':<15} {'Traditional':<10} {'Enhanced':<10} {'Additional':<10} {'Perf. Impact':<15}")
    print("-" * 60)
    
    for location, results in all_results.items():
        perf_impact = (results["enhanced_time"] / results["traditional_time"]) - 1 if results["traditional_time"] > 0 else 0
        print(f"{location:<15} {results['traditional_count']:<10} {results['enhanced_count']:<10} {results['additional_count']:<10} {perf_impact:.2%}") 