import os
import django
import time

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q
from final_search_implementation import enhanced_component_search

def test_bidirectional_search(location_name, expected_outcode):
    """
    Test searching by location name to find results with the associated postcode
    """
    print(f"\n{'='*80}")
    print(f"TESTING BIDIRECTIONAL SEARCH: '{location_name}' (should find components with {expected_outcode})")
    print(f"{'='*80}")
    
    # Run traditional search with just the location name
    traditional_filter = (
        Q(location__icontains=location_name)      |
        Q(description__icontains=location_name)   |
        Q(technology__icontains=location_name)    |
        Q(company_name__icontains=location_name)  |
        Q(cmu_id__icontains=location_name)
    )
    traditional_results = Component.objects.filter(traditional_filter).distinct()
    traditional_count = traditional_results.count()
    
    # Run enhanced search
    enhanced_results = enhanced_component_search(location_name, limit=20)
    
    # Filter for components with the expected outcode that DON'T have the location name
    outcode_filter = Q(outward_code__istartswith=expected_outcode)
    location_exclusion = ~Q(location__icontains=location_name)
    outcode_only_components = Component.objects.filter(outcode_filter & location_exclusion)[:20]
    outcode_only_count = outcode_only_components.count()
    
    # Check enhanced results for any of these outcode-only components
    enhanced_ids = set(component.id for component in enhanced_results)
    outcode_only_ids = set(component.id for component in outcode_only_components)
    matching_ids = enhanced_ids.intersection(outcode_only_ids)
    
    # Print search statistics
    print(f"Traditional search found {traditional_count} results with '{location_name}' in text")
    print(f"There are {outcode_only_count} components with '{expected_outcode}' outcode but no '{location_name}' in text")
    print(f"Enhanced search returned {len(enhanced_results)} results, including {len(matching_ids)} components with '{expected_outcode}' but no '{location_name}'")
    
    # Print each result with key field values
    print("\n--- Enhanced Search Results ---")
    for i, component in enumerate(enhanced_results):
        is_outcode_only = component.id in outcode_only_ids
        marker = "* OUTCODE MATCH *" if is_outcode_only else ""
        
        print(f"\n{i+1}. {component.location} {marker}")
        if component.company_name:
            print(f"   Company: {component.company_name}")
        if hasattr(component, 'outward_code') and component.outward_code:
            print(f"   Outward code: {component.outward_code}")
    
    return enhanced_results

if __name__ == "__main__":
    # Test bidirectional mapping for key locations
    location_outcode_pairs = [
        ("battersea", "SW11"),
        ("peckham", "SE15"),
        ("nottingham", "NG")
    ]
    
    for location, outcode in location_outcode_pairs:
        test_bidirectional_search(location, outcode) 