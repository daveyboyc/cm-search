"""
New map test view for improved outward_code filtering
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from .decorators.access_required import map_access_required

@map_access_required
def map_search_fixed_view(request):
    """View for testing improved SW11 search with outward_code filtering"""
    
    # Default search query
    search_query = request.GET.get('q', 'SW11')
    
    # Context for template
    context = {
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'search_query': search_query
    }
    
    return render(request, 'checker/map_search_simple_fixed.html', context)