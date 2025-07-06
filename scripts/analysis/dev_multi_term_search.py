import os
import django
import time

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q
from final_search_implementation import enhanced_component_search

def test_multi_term_search(query, limit=10):
    """
    Test the enhanced search with a multi-term query and show detailed scoring
    """
    print(f"\n{'='*80}")
    print(f"TESTING MULTI-TERM SEARCH: '{query}'")
    print(f"{'='*80}")
    
    query_lower = query.lower()
    query_words = query_lower.split()
    
    # Location mapping for scoring explanation
    location_to_outcode = {
        "peckham": "SE15",
        "nottingham": "NG",
        "manchester": "M",
        "birmingham": "B",
    }
    
    # Base filter for comparison
    base_filter = (
        Q(location__icontains=query)      |
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)
    )
    
    # Get components using our search implementation
    start_time = time.time()
    
    # Get matching components (we'll re-score for display)
    base_results = Component.objects.filter(base_filter).distinct()[:100]
    base_count = base_results.count()
    
    # Apply standard enhanced filter for comparison
    enhanced_filter = base_filter | Q(county__icontains=query) | Q(outward_code__icontains=query)
    
    # Add special location filters
    location_outward_filter = Q()
    for word in query_words:
        if word in location_to_outcode and location_to_outcode[word]:
            outcode = location_to_outcode[word]
            location_outward_filter |= Q(outward_code__istartswith=outcode)
    
    enhanced_filter |= location_outward_filter
    enhanced_results = Component.objects.filter(enhanced_filter).distinct()[:100]
    enhanced_count = enhanced_results.count()
    
    # Manually score each result to show detailed breakdown
    scored_components = []
    
    # Get all potential matches for manual scoring
    all_potential_matches = enhanced_results
    
    for component in all_potential_matches:
        # Start with baseline score
        relevance_score = 0.1
        
        # Prepare for scoring explanation
        scoring_explanation = []
        
        # Get component fields
        location = (component.location or "").lower()
        county = (component.county or "").lower()
        outward = (component.outward_code or "").lower()
        tech = (component.technology or "").lower()
        description = (component.description or "").lower()
        
        # Check for exact matches of the complete query
        if query_lower in location:
            # Highest priority - exact phrase in location
            relevance_score += 5.0
            scoring_explanation.append(f"Full phrase '{query_lower}' in location: +5.0")
        
        # For multi-word searches, check each word individually
        direct_match_count = 0
        word_match_explanations = []
        
        for word in query_words:
            # Check each word against each field
            if word in location:
                # Direct location match (most important)
                relevance_score += 2.0
                direct_match_count += 1
                word_match_explanations.append(f"'{word}' in location: +2.0")
            elif word in tech:
                # Technology match
                relevance_score += 1.0
                word_match_explanations.append(f"'{word}' in technology: +1.0")
            elif word in description:
                # Description match
                relevance_score += 0.8
                word_match_explanations.append(f"'{word}' in description: +0.8")
            elif word in county:
                # County match
                relevance_score += 0.5
                word_match_explanations.append(f"'{word}' in county: +0.5")
            elif word in outward:
                # Direct outward code match
                relevance_score += 0.3
                word_match_explanations.append(f"'{word}' in outward code: +0.3")
            elif word in location_to_outcode and location_to_outcode[word]:
                # Location's outward code match (lowest priority)
                outcode = location_to_outcode[word].lower()
                if outward.startswith(outcode):
                    relevance_score += 0.2
                    word_match_explanations.append(f"'{word}' matched via outward code {outcode}: +0.2")
        
        scoring_explanation.extend(word_match_explanations)
        
        # Special boost if all query words matched directly in the location
        if direct_match_count == len(query_words) and len(query_words) > 1:
            relevance_score += 3.0
            scoring_explanation.append(f"All {len(query_words)} words directly in location: +3.0")
        
        # Add component with its score and explanation
        scored_components.append({
            "component": component,
            "relevance_score": relevance_score,
            "explanation": scoring_explanation
        })
    
    # Sort by relevance score (highest first)
    scored_components.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # Now let's call our actual implementation
    search_time = time.time() - start_time
    actual_results = enhanced_component_search(query, limit=limit)
    
    # Print results of the manual scoring (for explanation)
    print(f"Basic search found {base_count} results")
    print(f"Enhanced search found {enhanced_count} results")
    print(f"Search completed in {search_time:.3f} seconds")
    
    print("\n--- Top Results with Score Explanations ---")
    for i, result in enumerate(scored_components[:limit]):
        component = result["component"]
        score = result["relevance_score"]
        explanation = result["explanation"]
        
        print(f"\n{i+1}. [{score:.1f}] {component.location}")
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
        
        print("   --- Score Explanation ---")
        print(f"   Base score: 0.1")
        for exp in explanation:
            print(f"   {exp}")
        print(f"   Total: {score:.1f}")
    
    # Now verify our actual implementation would return the same top results
    print("\n=== Verification of Implementation ===")
    print(f"Our enhanced_component_search function returned {len(actual_results)} results")
    
    if len(actual_results) > 0:
        print("Top result from implementation:", actual_results[0].location)
        print("Top result from test:", scored_components[0]["component"].location)
        
        # Check if top results match
        if actual_results[0].id == scored_components[0]["component"].id:
            print("✓ Implementation produces the same top result")
        else:
            print("✗ Implementation produces different top result - check scoring logic")
    
    return scored_components[:limit]

if __name__ == "__main__":
    # Test multi-term queries
    test_queries = [
        "hospital in peckham",
        "battery in nottingham",
        "solar farm manchester",
        "nottingham power station"
    ]
    
    for query in test_queries:
        test_multi_term_search(query) 