"""
Enhanced search function with county/outward_code support
This can be integrated into your existing search views
"""
from django.db.models import Q
from checker.models import Component

def enhanced_component_search(query, limit=20):
    """
    Enhanced component search that leverages county and outward_code fields
    with special handling for location searches, while maintaining keyword search capabilities.
    """
    query_lower = query.lower()
    query_words = query_lower.split()
    
    # Location to outcode mapping
    # Keep the original variable name for backward compatibility
    location_to_outcode = {
        "peckham": "SE15",
        "battersea": "SW11",
        "nottingham": "NG",
        "manchester": "M",
        "birmingham": "B",
        "london": None  # Too many outward codes to list for London
    }
    
    # Create reverse mapping but don't use it directly in the main filter
    # to avoid unexpected results
    outcode_to_location = {v: k for k, v in location_to_outcode.items() if v}
    
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
    
    # Outward code filter for direct outward code searches (e.g., "SE15")
    outward_filter = Q(outward_code__icontains=query)
    
    # Special location filter - for known locations, match by outward code
    # This is the original behavior
    location_outward_filter = Q()
    if query_lower in location_to_outcode and location_to_outcode[query_lower]:
        outcode = location_to_outcode[query_lower]
        location_outward_filter |= Q(outward_code__istartswith=outcode)
    
    # Also check individual words in multi-word queries
    for word in query_words:
        if word in location_to_outcode and location_to_outcode[word]:
            outcode = location_to_outcode[word]
            location_outward_filter |= Q(outward_code__istartswith=outcode)
    
    # Combine all filters
    combined_filter = base_filter | county_filter | outward_filter | location_outward_filter
    
    # Get matching components
    matching_components = Component.objects.filter(combined_filter).distinct()[:500]
    
    # Apply relevance scoring
    scored_components = []
    for component in matching_components:
        # Start with baseline score
        relevance_score = 0.1
        
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
        
        # For multi-word searches, check each word individually and add scores
        direct_match_count = 0
        for word in query_words:
            # Check each word against each field
            if word in location:
                # Direct location match (most important)
                relevance_score += 2.0
                direct_match_count += 1
            elif word in tech:
                # Technology match
                relevance_score += 1.0
            elif word in description:
                # Description match
                relevance_score += 0.8
            elif word in county:
                # County match
                relevance_score += 0.5
            elif word in outward:
                # Direct outward code match
                relevance_score += 0.3
            elif word in location_to_outcode and location_to_outcode[word]:
                # Location's outward code match
                outcode = location_to_outcode[word].lower()
                if outward.startswith(outcode):
                    relevance_score += 0.2
        
        # Special boost if all query words matched directly in the location
        if direct_match_count == len(query_words) and len(query_words) > 1:
            relevance_score += 3.0
        
        # Add component with its score
        scored_components.append({
            "component": component,
            "relevance_score": relevance_score
        })
    
    # Sort by relevance score (highest first)
    scored_components.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # Extract just the components (without scores) for return
    components = [item["component"] for item in scored_components[:limit]]
    
    return components

# Example of how to integrate this into your existing view
"""
def component_search_view(request):
    query = request.GET.get('q', '')
    if query:
        # Use the enhanced search
        components = enhanced_component_search(query, limit=50)
    else:
        # Return recent components or something similar
        components = Component.objects.all().order_by('-id')[:50]
    
    context = {
        'components': components,
        'query': query
    }
    
    return render(request, 'components/search_results.html', context)
""" 