"""
Test view for the new location-based search.
"""
from django.shortcuts import render
from .services.location_search import search_locations

def test_location_search_html(request):
    """Test view that renders HTML results."""
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Use the new location search
    results = search_locations(query, page, per_page, sort_by, sort_order)
    
    # Add extra context for template
    context = {
        **results,
        'total_components': sum(lg.component_count for lg in results['location_groups']),
    }
    
    return render(request, 'checker/location_search_results.html', context)


def test_location_search_styled(request):
    """Test view with current search results styling."""
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))  # Default 20 like current
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Use the new location search
    results = search_locations(query, page, per_page, sort_by, sort_order)
    
    # Add extra context for template
    context = {
        **results,
        'total_components': sum(lg.component_count for lg in results['location_groups']),
    }
    
    return render(request, 'checker/search_location_based.html', context)

def test_location_search(request):
    """Test view for location-based search."""
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Use the new location search
    results = search_locations(query, page, per_page, sort_by, sort_order)
    
    # For now, just render as JSON for testing
    from django.http import JsonResponse
    
    # Convert LocationGroup objects to dict for JSON serialization
    location_data = []
    for lg in results['location_groups']:
        location_data.append({
            'location': lg.location,
            'component_count': lg.component_count,
            'capacity': lg.get_display_capacity(),
            'primary_technology': lg.get_primary_technology(),
            'primary_company': lg.get_primary_company(),
            'descriptions': lg.descriptions[:3] if lg.descriptions else [],  # First 3 descriptions
        })
    
    return JsonResponse({
        'query': query,
        'total_locations': results['total_locations'],
        'total_components': results['total_components'],
        'page': page,
        'locations': location_data,
        'debug_info': results['debug_info'],
    })