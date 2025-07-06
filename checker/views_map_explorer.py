"""
Mobile-optimized map explorer view
Clean map interface with responsive filter layout
"""
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.db import connection
import logging
import time

from .models import LocationGroup, Component
from .services.filter_options import get_complete_filter_options
from .decorators.access_required import map_access_required

logger = logging.getLogger(__name__)

@map_access_required
def map_explorer_view(request):
    """
    New mobile-optimized map explorer with responsive filter layout
    Features:
    - Universal search navbar integration
    - Desktop: Filters on left sidebar
    - Mobile: Filters on top, collapsible
    - Standard Google Map with working mobile controls
    """
    start_time = time.time()
    
    # Get search query from navbar
    query = request.GET.get('q', '').strip()
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')  # Default to 'all' to show both active and inactive
    technology_filter = request.GET.get('technology', '')
    company_filter = request.GET.get('company', '')
    
    # Use cached filter options for performance (like search-map)
    logger.info("🚀 Using cached filter approach for map explorer")
    filter_start = time.time()
    
    cached_options = get_complete_filter_options()
    technologies = cached_options['technologies']
    companies = cached_options['companies']
    
    # Get ALL companies (excluding residential DSR) - sorted by unique locations for map relevance
    from django.db.models import Count
    from django.db import connection
    
    # Get companies with their location counts (more relevant for map explorer)
    # Always show ALL companies regardless of status filter - filtering happens at map data level
    with connection.cursor() as cursor:
        cursor.execute("""
            WITH location_counts AS (
                SELECT 
                    jsonb_object_keys(lg.companies) as company_name,
                    COUNT(DISTINCT lg.id) as location_count
                FROM checker_locationgroup lg
                WHERE lg.companies IS NOT NULL
                GROUP BY jsonb_object_keys(lg.companies)
            ),
            ranked_companies AS (
                SELECT company_name, location_count,
                       ROW_NUMBER() OVER (ORDER BY location_count DESC) as rank
                FROM location_counts
                WHERE company_name IS NOT NULL
                AND company_name != ''
            )
            SELECT company_name, location_count as count
            FROM ranked_companies
            WHERE location_count > 7  -- Companies with more than 7 locations
            ORDER BY location_count DESC
        """)
        
        top_companies = [
            {'company_name': row[0], 'count': row[1]} 
            for row in cursor.fetchall()
        ]
        
        # Add "Everything else" option to bundle small companies (≤7 locations)
        cursor.execute("""
            WITH location_counts AS (
                SELECT 
                    jsonb_object_keys(lg.companies) as company_name,
                    COUNT(DISTINCT lg.id) as location_count
                FROM checker_locationgroup lg
                WHERE lg.companies IS NOT NULL
                GROUP BY jsonb_object_keys(lg.companies)
            )
            SELECT COUNT(*) as small_company_count, SUM(location_count) as total_small_locations
            FROM location_counts
            WHERE company_name IS NOT NULL
            AND company_name != ''
            AND location_count <= 7
        """)
        
        small_company_stats = cursor.fetchone()
        small_company_count = small_company_stats[0] or 0
        small_total_locations = small_company_stats[1] or 0
        
        # Add "Everything else" option if there are small companies
        if small_company_count > 0:
            top_companies.append({
                'company_name': 'Everything else', 
                'count': small_total_locations
            })
    
    # Get delivery year options (same as map view)
    delivery_years = Component.objects.exclude(delivery_year__isnull=True)\
                                .exclude(delivery_year='')\
                                .values_list('delivery_year', flat=True)\
                                .distinct()\
                                .order_by('-delivery_year') # Newest first
    
    filter_time = time.time() - filter_start
    logger.info(f"✅ Cached filters: {len(technologies)} techs, {len(companies)} companies, {len(delivery_years)} years in {filter_time:.3f}s")
    
    # Get basic stats for map info
    stats_start = time.time()
    
    # Get total counts efficiently
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_locations,
                SUM(component_count) as total_components,
                COUNT(*) FILTER (WHERE is_active = true) as active_locations
            FROM checker_locationgroup
        """)
        stats = cursor.fetchone()
        total_locations = stats[0] or 0
        total_components = stats[1] or 0
        active_locations = stats[2] or 0
    
    stats_time = time.time() - stats_start
    
    # Prepare context
    context = {
        'query': query,
        'search_query': query,  # For template compatibility
        'api_key': settings.GOOGLE_MAPS_API_KEY if hasattr(settings, 'GOOGLE_MAPS_API_KEY') else '',
        
        # Filter options
        'technologies': technologies,
        'companies': companies,
        'top_companies': top_companies,
        
        # Current filter values
        'status_filter': status_filter,
        'technology_filter': technology_filter,
        'company_filter': company_filter,
        
        # Statistics
        'total_locations': total_locations,
        'total_components': total_components,
        'active_locations': active_locations,
        
        # Performance metrics
        'load_time': time.time() - start_time,
        'filter_time': filter_time,
        'stats_time': stats_time,
    }
    
    logger.info(f"🗺️  Map Explorer loaded in {context['load_time']:.3f}s")
    logger.info(f"   📊 Stats: {total_locations} locations, {total_components} components")
    logger.info(f"   🔧 Filters: status={status_filter}, tech={technology_filter}, company={company_filter}")
    logger.info(f"   🏢 Top companies: {len(top_companies)} companies loaded")
    
    return render(request, 'checker/map_explorer.html', context)