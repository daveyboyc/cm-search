"""
View for displaying search results on a map
"""
from django.shortcuts import render, redirect
from django.conf import settings
from .decorators.access_required import map_access_required
# from monitoring.decorators import monitor_api_endpoint, monitor_map_api, monitor_search_api, monitor_component_detail

# @monitor_api_endpoint("/map_results/")  # Temporarily disabled
@map_access_required
def map_search_results_view(request):
    """
    View for displaying search results on a map.
    Takes a search query or company filter and displays matching components on a map.
    """
    # Get search query and filters from request
    search_query = request.GET.get('q', '')
    company_filter = request.GET.get('company', '')
    tech_filter = request.GET.get('tech', '')
    
    # Get additional filter parameters
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # If we have a company filter, use it as the search query
    if company_filter and not search_query:
        search_query = company_filter
    
    # If we have a tech filter, use it as the search query
    if tech_filter and not search_query:
        search_query = tech_filter
    
    # Redirect to main search if no query or filter provided
    if not search_query:
        return redirect('/')
    
    # Prepare context for template
    context = {
        'search_query': search_query,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
    }
    
    # Render map search results template
    return render(request, 'checker/map_search_results.html', context)