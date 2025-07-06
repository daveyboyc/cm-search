"""
CMU Map View - Shows all locations for a specific CMU ID on an interactive map
Similar to company-map and technology-map views
"""
import time
import urllib.parse
import logging
from django.shortcuts import render
from django.conf import settings
from django.core.paginator import Paginator
from .models import LocationGroup, Component
from .decorators.bot_protection import bot_protected_view

logger = logging.getLogger(__name__)


@bot_protected_view(rate='10/m')
def cmu_detail_map(request, cmu_id):
    """
    Map view for CMU locations - similar to company and technology map views
    Shows all locations for a specific CMU ID on an interactive map
    """
    start_time = time.time()
    
    # MONITORING: Count database queries
    from django.db import connection
    queries_before = len(connection.queries)
    
    # Decode CMU ID (handle URL encoding)
    cmu_display = urllib.parse.unquote(cmu_id)
    
    # Get parameters
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', '')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    technology_filter = request.GET.get('technology', '')
    
    # CMU pages are filtered views, not search results - default to location sorting
    if sort_by == 'relevance':
        sort_by = 'location'
    
    # Find all Components with this CMU ID, then get their LocationGroups
    components_with_cmu = Component.objects.filter(cmu_id=cmu_display).values_list('location', flat=True).distinct()
    
    # Find all LocationGroups with locations that have this CMU ID
    location_groups = LocationGroup.objects.filter(
        location__in=components_with_cmu
    )
    
    # Apply status filtering
    if status_filter == 'active':
        location_groups = location_groups.filter(is_active=True)
    elif status_filter == 'inactive':
        location_groups = location_groups.filter(is_active=False)
    
    # Apply auction year filtering at database level
    if auction_filter and auction_filter != 'all':
        location_groups = location_groups.filter(
            auction_years__icontains=auction_filter
        )
    
    # Apply technology filtering
    if technology_filter and technology_filter != 'all':
        location_groups = location_groups.filter(technologies__has_key=technology_filter)
    
    # PERFORMANCE: Use lazy loading for filters - load via AJAX on dropdown interaction
    filter_start = time.time()
    
    # Show dropdowns with placeholder content - populated by AJAX when clicked
    sorted_auction_years = ['Loading...']
    sorted_technologies = ['Loading...']
    
    timings = {'lazy_filters': time.time() - filter_start}
    logger.info("🚀 CMU view using lazy loading - filters will load on dropdown interaction")
    
    # Apply sorting
    if sort_by == 'location':
        location_groups = location_groups.order_by('location' if sort_order != 'desc' else '-location')
    elif sort_by == 'capacity':
        location_groups = location_groups.order_by('-normalized_capacity_mw' if sort_order != 'desc' else 'normalized_capacity_mw')
    elif sort_by == 'components':
        location_groups = location_groups.order_by('-component_count' if sort_order != 'desc' else 'component_count')
    else:  # Default to relevance (capacity)
        location_groups = location_groups.order_by('-normalized_capacity_mw')
    
    # Get total counts
    total_locations = location_groups.count()
    total_capacity = sum(lg.normalized_capacity_mw or 0 for lg in location_groups)
    
    # Add pagination
    paginator = Paginator(location_groups, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)
    
    # MONITORING: Track performance
    queries_after = len(connection.queries)
    query_count = queries_after - queries_before
    processing_time = time.time() - start_time
    
    logger.info(f"🗺️  EGRESS-OPTIMIZED CMU map for '{cmu_display}':")
    logger.info(f"   📊 Results: {total_locations} locations, {total_capacity:.1f}MW")
    logger.info(f"   ⚡ Performance: {processing_time:.3f}s, {query_count} queries")
    logger.info(f"   🔍 First few locations: {[lg.location for lg in location_groups[:3]]}")
    
    # Prepare context similar to company map
    context = {
        'cmu_id': cmu_display,
        'cmu_display': cmu_display,
        'location_groups': location_groups,
        'page_obj': page_obj,
        'total_locations': total_locations,
        'total_capacity': total_capacity,
        'query_time': processing_time,
        'query_count': query_count,
        
        # Filters
        'sort_by': sort_by,
        'sort_order': sort_order,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'technology_filter': technology_filter,
        
        # Filter options (for filter_bar_map.html compatibility)
        'auction_years': sorted_auction_years,
        'technologies': sorted_technologies,
        
        # Meta information
        'page_title': f'CMU {cmu_display} Locations Map',
        'meta_description': f'Interactive map showing all locations for CMU {cmu_display} in the capacity market.',
        
        # API key for Google Maps
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    
    return render(request, 'checker/search_cmu_map.html', context)