import os
import django
import time

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q

def simple_search(query):
    """Traditional search without county/outward_code"""
    filter_query = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)
    )
    return Component.objects.filter(filter_query).distinct()

def enhanced_search(query):
    """Enhanced search with county/outward_code"""
    filter_query = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)        |
        Q(county__icontains=query)        |   # Add county
        Q(outward_code__icontains=query)      # Add outward_code
    )
    return Component.objects.filter(filter_query).distinct()

def enhanced_search_with_relevance(query, limit=20):
    """Enhanced search with relevance ranking"""
    # Create the base filter for all potential matches
    filter_query = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)        |
        Q(county__icontains=query)        |   # Add county
        Q(outward_code__icontains=query)      # Add outward_code
    )
    
    # Get all matching components
    matching_components = Component.objects.filter(filter_query).distinct()[:500]
    
    # Create a list to store components with relevance scores
    scored_components = []
    
    for component in matching_components:
        # Default low relevance
        relevance_score = 0.1
        
        # Check for matches in each field and assign relevance
        location = (component.location or "").lower()
        county = (component.county or "").lower()
        outward = (component.outward_code or "").lower()
        
        if query.lower() in location:
            # Highest priority - direct location match
            relevance_score = 3.0
        elif query.lower() in county:
            # High priority - county match
            relevance_score = 2.0
        elif query.lower() in outward:
            # Medium priority - outward code match
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

def test_search_comparison(query):
    """Compare traditional and enhanced search results"""
    print(f"\n{'='*80}")
    print(f"TESTING SEARCH FOR: '{query}'")
    print(f"{'='*80}")
    
    # Test traditional search
    start_time = time.time()
    traditional_results = simple_search(query)
    traditional_time = time.time() - start_time
    traditional_count = traditional_results.count()
    
    print(f"Traditional search found {traditional_count} results in {traditional_time:.3f} seconds")
    
    # Test enhanced search
    start_time = time.time()
    enhanced_results = enhanced_search(query)
    enhanced_time = time.time() - start_time
    enhanced_count = enhanced_results.count()
    
    print(f"Enhanced search found {enhanced_count} results in {enhanced_time:.3f} seconds")
    
    # Calculate additional results
    traditional_ids = set(traditional_results.values_list('id', flat=True))
    enhanced_ids = set(enhanced_results.values_list('id', flat=True))
    additional_ids = enhanced_ids - traditional_ids
    additional_count = len(additional_ids)
    
    print(f"Additional results found: {additional_count}")
    
    # Show sample of traditional results
    print("\n--- Traditional Search Results Sample ---")
    for i, result in enumerate(traditional_results[:5]):
        print(f"{i+1}. {result.location} (ID: {result.id})")
        if hasattr(result, 'county') and result.county:
            print(f"   County: {result.county}")
        if hasattr(result, 'outward_code') and result.outward_code:
            print(f"   Outward code: {result.outward_code}")
    
    # Show sample of additional results
    if additional_count > 0:
        print("\n--- Additional Results from Enhanced Search ---")
        additional_results = Component.objects.filter(id__in=additional_ids)
        for i, result in enumerate(additional_results[:5]):
            print(f"{i+1}. {result.location} (ID: {result.id})")
            if hasattr(result, 'county') and result.county:
                print(f"   County: {result.county}")
            if hasattr(result, 'outward_code') and result.outward_code:
                print(f"   Outward code: {result.outward_code}")
    
    # Test relevance-based search
    print("\n--- Enhanced Search with Relevance Ranking ---")
    ranked_results = enhanced_search_with_relevance(query, limit=10)
    print(f"Top {len(ranked_results)} results by relevance:")
    for i, result in enumerate(ranked_results):
        component = result["component"]
        score = result["relevance_score"]
        print(f"{i+1}. [{score:.1f}] {component.location} (ID: {component.id})")
        if hasattr(component, 'county') and component.county:
            print(f"   County: {component.county}")
        if hasattr(component, 'outward_code') and component.outward_code:
            print(f"   Outward code: {component.outward_code}")
    
    return {
        "traditional_count": traditional_count,
        "enhanced_count": enhanced_count,
        "additional_count": additional_count,
        "traditional_time": traditional_time,
        "enhanced_time": enhanced_time
    }

if __name__ == "__main__":
    # List of test queries
    test_queries = [
        "peckham",
        "nottingham",
        "manchester",
        "london",
        "NG1",  # Test postcode
        "SE15", # Test postcode
        "battery" # Test technology keyword
    ]
    
    # Run tests
    results = {}
    for query in test_queries:
        results[query] = test_search_comparison(query)
    
    # Print summary
    print("\n\n==== SEARCH TEST SUMMARY ====")
    print(f"{'Query':<15} {'Traditional':<12} {'Enhanced':<12} {'Additional':<12} {'Perf. Impact':<15}")
    print("-" * 65)
    
    for query, data in results.items():
        perf_impact = (data["enhanced_time"] / data["traditional_time"]) - 1 if data["traditional_time"] > 0 else 0
        print(f"{query:<15} {data['traditional_count']:<12} {data['enhanced_count']:<12} {data['additional_count']:<12} {perf_impact:+.2%}") 