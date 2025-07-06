import os
import django
import time

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q
from final_search_implementation import enhanced_component_search

def test_search_query(query, limit=10):
    """
    Test a specific search query and show results with explanations
    """
    print(f"\n{'='*80}")
    print(f"TESTING SEARCH: '{query}'")
    print(f"{'='*80}")
    
    # Use our implementation
    start_time = time.time()
    results = enhanced_component_search(query, limit=limit)
    search_time = time.time() - start_time
    
    # For comparison, run a traditional search
    traditional_filter = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)
    )
    traditional_results = Component.objects.filter(traditional_filter).distinct()
    traditional_count = traditional_results.count()
    
    # Print search statistics
    print(f"Traditional search found {traditional_count} results")
    print(f"Enhanced search returned {len(results)} results (limited to {limit})")
    print(f"Search completed in {search_time:.3f} seconds")
    
    # Print each result with key field values
    print("\n--- Top Results ---")
    for i, component in enumerate(results):
        print(f"\n{i+1}. {component.location}")
        if component.company_name:
            print(f"   Company: {component.company_name}")
        if component.technology:
            print(f"   Technology: {component.technology}")
        if component.description:
            description_preview = component.description[:100] + "..." if len(component.description) > 100 else component.description
            print(f"   Description: {description_preview}")
        if hasattr(component, 'county') and component.county:
            print(f"   County: {component.county}")
        if hasattr(component, 'outward_code') and component.outward_code:
            print(f"   Outward code: {component.outward_code}")
    
    # Check if enhanced search found results not in traditional search
    enhanced_ids = set(component.id for component in results)
    traditional_ids = set(traditional_results.values_list('id', flat=True))
    new_result_ids = enhanced_ids - traditional_ids
    
    if new_result_ids:
        print(f"\nFound {len(new_result_ids)} results that would not appear in traditional search!")
        for component_id in new_result_ids:
            component = next((c for c in results if c.id == component_id), None)
            if component:
                print(f"- {component.location} (ID: {component.id})")
                if hasattr(component, 'county') and component.county:
                    print(f"  County: {component.county}")
                if hasattr(component, 'outward_code') and component.outward_code:
                    print(f"  Outward code: {component.outward_code}")
    
    return results

if __name__ == "__main__":
    # Test various search queries
    test_queries = [
        "SW11",                     # Direct postcode search
        "SW",                       # Partial postcode search
        "battersea",                # Location name (related to SW11)
        "energy storage in London", # Multi-word with location and technology
        "OCGT",                     # Technology-specific search
        "Veolia",                   # Company name search
        "hospital SW11"             # Combined facility + postcode
    ]
    
    for query in test_queries:
        test_search_query(query) 