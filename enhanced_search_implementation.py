import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q

def enhanced_component_search(query, limit=20):
    """
    Enhanced component search that uses county and outward_code fields
    with special handling for location searches.
    """
    query_lower = query.lower()
    
    # Location -> outcode mapping for common locations
    # This is still needed for locations where we want to match components by outward code
    location_to_outcode = {
        "peckham": "SE15",
        "nottingham": "NG",
        "manchester": "M",
        "birmingham": "B",
        "london": None  # Too many outward codes to list for London
    }
    
    # Base filter (always applied)
    base_filter = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)
    )
    
    # County filter - direct county name match
    county_filter = Q(county__icontains=query)
    
    # Outward code filter for direct outward code searches
    outward_filter = Q(outward_code__icontains=query)
    
    # Special location filter - for known locations, match by outward code
    location_outward_filter = Q()
    if query_lower in location_to_outcode and location_to_outcode[query_lower]:
        outcode = location_to_outcode[query_lower]
        location_outward_filter = Q(outward_code__istartswith=outcode)
    
    # Combine all filters
    combined_filter = base_filter | county_filter | outward_filter | location_outward_filter
    
    # Get matching components
    matching_components = Component.objects.filter(combined_filter).distinct()[:500]
    
    # Apply relevance scoring
    scored_components = []
    for component in matching_components:
        # Default score
        relevance_score = 0.1
        
        location = (component.location or "").lower()
        county = (component.county or "").lower()
        outward = (component.outward_code or "").lower()
        
        # Check for matches in each field and assign relevance
        if query_lower in location:
            # Highest priority - direct location match
            relevance_score = 3.0
        elif query_lower in county:
            # High priority - county match 
            relevance_score = 2.0
        elif query_lower in outward:
            # Medium priority - outward code direct match
            relevance_score = 1.5
        elif query_lower in location_to_outcode and location_to_outcode[query_lower]:
            # Check if component's outward code matches the location's outward code
            outcode = location_to_outcode[query_lower].lower()
            if outward.startswith(outcode):
                # Location-based outward code match
                relevance_score = 1.0
        
        # Add component with its score
        scored_components.append({
            "component": component,
            "relevance_score": relevance_score
        })
    
    # Sort by relevance score (highest first)
    scored_components.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # Return limited results
    return scored_components[:limit]

# Test function for a single query
def test_search(query, limit=10):
    """Test the enhanced search for a single query"""
    print(f"\n{'='*80}")
    print(f"TESTING ENHANCED SEARCH FOR: '{query}'")
    print(f"{'='*80}")
    
    # Get traditional search results (for comparison)
    traditional_filter = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)
    )
    traditional_results = Component.objects.filter(traditional_filter).distinct()
    traditional_count = traditional_results.count()
    
    # Get enhanced search results
    enhanced_results = enhanced_component_search(query, limit=limit)
    
    # Get IDs from traditional search
    traditional_ids = set(traditional_results.values_list('id', flat=True))
    
    # Get IDs from enhanced search results
    enhanced_ids = set(item["component"].id for item in enhanced_results)
    
    # Find new results (in enhanced but not in traditional)
    new_result_ids = enhanced_ids - traditional_ids
    
    print(f"Traditional search found {traditional_count} results")
    print(f"Enhanced search returned {len(enhanced_results)} results (limited to {limit})")
    print(f"New results not in traditional search: {len(new_result_ids)}")
    
    # Print enhanced search results
    print("\n--- Enhanced Search Results ---")
    for i, result in enumerate(enhanced_results):
        component = result["component"]
        score = result["relevance_score"]
        is_new = component.id in new_result_ids
        new_marker = "NEW!" if is_new else ""
        
        print(f"{i+1}. [{score:.1f}] {component.location} {new_marker}")
        if component.company_name:
            print(f"   Company: {component.company_name}")
        if hasattr(component, 'county') and component.county:
            print(f"   County: {component.county}")
        if hasattr(component, 'outward_code') and component.outward_code:
            print(f"   Outward code: {component.outward_code}")
    
    return {
        "traditional_count": traditional_count,
        "enhanced_count": len(enhanced_results),
        "new_results": len(new_result_ids)
    }

if __name__ == "__main__":
    # Test some queries
    test_queries = [
        "peckham",      # Location with specific outcode
        "nottingham",   # Location with county and outcode
        "battery",      # Technology keyword
        "SE15",         # Direct outcode
        "hospital"      # Facility keyword
    ]
    
    for query in test_queries:
        test_search(query) 