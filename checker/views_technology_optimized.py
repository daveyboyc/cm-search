"""
Optimized technology view using LocationGroup for high performance
"""
import logging
import time
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from django.conf import settings
import urllib.parse

from .models import LocationGroup, Component
from .templatetags.checker_tags import technology_color
from .decorators.access_required import map_access_required
from .decorators.bot_protection import bot_protected_view

logger = logging.getLogger(__name__)

# Monitoring import
try:
    from monitoring.decorators import monitor_api
except ImportError:
    def monitor_api(func):
        return func

@monitor_api
@gzip_page
@map_access_required
@bot_protected_view(rate='5/m')  # Strict rate limiting for bots
# @cache_page(60 * 5)  # Disabled to prevent Redis memory issues - pages are fast enough without cache  
def technology_detail_map(request, technology_name):
    """
    Technology detail view with map layout (based on search-map template)
    Shows all locations with components of this technology
    """
    start_time = time.time()
    
    # Initialize timing
    timings = {}
    
    # Get parameters
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))  # 25 per page for map view
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')  # all, active, inactive
    auction_filter = request.GET.get('auction', '')  # empty or specific auction year
    company_filter = request.GET.get('company', 'all')  # NEW: Company filtering
    
    # Technology pages are filtered views, not search results - default to location sorting
    if sort_by == 'relevance':
        sort_by = 'location'
    
    # Decode technology name (handle URL encoding)
    import urllib.parse
    technology_display = urllib.parse.unquote(technology_name)
    
    # Find all LocationGroups with this technology - use optimized query
    # Special handling for Interconnector umbrella category
    if technology_display.lower() == 'interconnector':
        # Use exact interconnector technology names from the database (as JSON keys)
        interconnector_techs = [
            'BritNED (Netherlands)', 'Eleclink (France)', 'EWIC (Ireland)', 
            'EWIC (Republic of Ireland)', 'Greenlink (Republic of Ireland)',
            'IFA2 (France)', 'IFA (France)', 'Moyle (Northern Ireland)',
            'NEMO (Belgium)', 'NeuConnect (Germany)', 'NSL (Norway)', 'VikingLink (Denmark)'
        ]
        
        # Build OR query for all interconnector types (technologies is a JSONField with exact keys)
        interconnector_query = Q()
        for tech_name in interconnector_techs:
            interconnector_query |= Q(technologies__has_key=tech_name)
        
        location_groups = LocationGroup.objects.filter(interconnector_query)
        logger.info(f"🔗 Interconnector umbrella search found {location_groups.count()} locations")
    else:
        # Standard technology search for other technologies
        location_groups = LocationGroup.objects.filter(
            technologies__icontains=technology_display
        )
    
    # OPTIMIZED: Apply status filtering at database level
    if status_filter == 'active':
        # Use pre-calculated is_active field for maximum performance
        location_groups = location_groups.filter(is_active=True)
    elif status_filter == 'inactive':
        # Use pre-calculated is_active field for maximum performance
        location_groups = location_groups.filter(is_active=False)
    
    # OPTIMIZED: Apply auction year filter at database level
    if auction_filter and auction_filter != 'all':
        location_groups = location_groups.filter(
            auction_years__icontains=auction_filter
        )
    
    # OPTIMIZED: Apply company filter at database level (PostgreSQL JSONB)
    if company_filter and company_filter != 'all':
        location_groups = location_groups.filter(companies__has_key=company_filter)
        logger.info(f"🔧 Applied company filter: {company_filter}")
    
    # PERFORMANCE: Use lazy loading for filters - load via AJAX on dropdown interaction
    # This eliminates expensive filter calculation from main page load
    filter_start = time.time()
    
    # Show dropdowns with placeholder content - populated by AJAX when clicked
    auction_years = ['Loading...']
    companies = ['Loading...']
    
    timings['lazy_filters'] = time.time() - filter_start
    logger.info("🚀 Technology view using lazy loading - filters will load on dropdown interaction")
    
    # Apply sorting
    if sort_by == 'location':
        location_groups = location_groups.order_by(
            'location' if sort_order == 'asc' else '-location'
        )
    elif sort_by == 'mw':
        location_groups = location_groups.order_by(
            '-normalized_capacity_mw' if sort_order == 'desc' else 'normalized_capacity_mw'
        )
    elif sort_by == 'components':
        location_groups = location_groups.order_by(
            '-component_count' if sort_order == 'desc' else 'component_count'
        )
    else:  # relevance (default)
        # For technology view, relevance = capacity
        location_groups = location_groups.order_by('-normalized_capacity_mw')
    
    # OPTIMIZED: Calculate totals using database aggregation
    totals = location_groups.aggregate(
        total_locations=Count('id'),
        total_capacity=Sum('normalized_capacity_mw'),
        total_components=Sum('component_count')
    )
    
    # OPTIMIZED: Select only needed fields and paginate BEFORE processing
    optimized_locations = location_groups.only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    # Pagination BEFORE creating list (key optimization!)
    paginator = Paginator(optimized_locations, per_page)
    page_obj = paginator.get_page(page)
    
    # Now convert only the current page to list with is_active calculation
    location_groups_list = []
    active_patterns = ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']
    
    for lg in page_obj:
        lg_dict = {
            'id': lg.id,
            'location': lg.location,
            'county': lg.county,
            'latitude': lg.latitude,
            'longitude': lg.longitude,
            'descriptions': lg.descriptions,
            'technologies': lg.technologies,
            'companies': lg.companies,
            'auction_years': lg.auction_years,
            'component_count': lg.component_count,
            'normalized_capacity_mw': lg.normalized_capacity_mw,
            'is_active': False
        }
        
        # Check if active (only for current page items)
        if lg.auction_years:
            lg_dict['is_active'] = any(
                pattern in year_str 
                for year_str in lg.auction_years 
                for pattern in active_patterns
            )
        
        location_groups_list.append(lg_dict)
    
    # Replace page_obj's object_list with our processed list
    page_obj.object_list = location_groups_list
    
    # Get technology color
    tech_color = technology_color(technology_display)
    
    load_time = time.time() - start_time
    logger.info(f"Technology map view for {technology_display} loaded in {load_time:.2f}s")
    
    context = {
        'technology_name': technology_display,
        'technology_color': tech_color,
        'page_obj': page_obj,
        'total_locations': totals['total_locations'] or 0,
        'total_components': totals['total_components'] or 0,
        'total_capacity': totals['total_capacity'] or 0,
        'auction_years': auction_years,
        'auction_filter': auction_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'timings': timings,
        'api_time': load_time,
        'sort_order': sort_order,
        'companies': companies,  # NEW: Company filter dropdown
        'company_filter': company_filter,  # NEW: Selected company filter
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        # Add missing variables for template compatibility
        'query': '',  # Technology maps don't have text queries
        'technologies': [],  # Not needed for technology-specific maps
    }
    
    return render(request, 'checker/search_technology_map.html', context)


@bot_protected_view(rate='5/m')  # Strict rate limiting for bots
def technology_detail_optimized(request, technology_name):
    """
    Optimized technology detail view using LocationGroup
    Shows all locations with components of this technology
    """
    start_time = time.time()
    
    # Get parameters
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    sort_by = request.GET.get('sort_by', 'capacity')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')  # all, active, inactive
    auction_filter = request.GET.get('auction', 'all')  # all or specific auction year
    company_filter = request.GET.get('company', 'all')  # NEW: Company filtering
    
    # Decode technology name (handle URL encoding)
    import urllib.parse
    technology_display = urllib.parse.unquote(technology_name)
    
    # Find all LocationGroups with this technology - use optimized query
    location_groups = LocationGroup.objects.filter(
        technologies__icontains=technology_display
    )
    
    # OPTIMIZED: Apply status filtering at database level
    if status_filter == 'active':
        # Use pre-calculated is_active field for maximum performance
        location_groups = location_groups.filter(is_active=True)
    elif status_filter == 'inactive':
        # Use pre-calculated is_active field for maximum performance
        location_groups = location_groups.filter(is_active=False)
    
    # OPTIMIZED: Apply auction year filter at database level
    if auction_filter != 'all':
        location_groups = location_groups.filter(
            auction_years__icontains=auction_filter
        )
    
    # OPTIMIZED: Apply company filter at database level (PostgreSQL JSONB)
    if company_filter and company_filter != 'all':
        location_groups = location_groups.filter(companies__has_key=company_filter)
        logger.info(f"🔧 Applied company filter: {company_filter}")
    
    # Apply sorting
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'components':
        order_field = 'component_count'
    elif sort_by == 'date':
        # Sort by the latest auction year
        order_field = 'auction_years__0'
    else:  # Default to capacity
        order_field = 'normalized_capacity_mw'
    
    if sort_order == 'desc' and order_field not in ['location']:
        order_field = f'-{order_field}'
    elif sort_order == 'asc' and order_field == 'location':
        pass
    elif sort_order == 'desc' and order_field == 'location':
        order_field = '-location'
    
    location_groups = location_groups.order_by(order_field)
    
    # Calculate technology-wide statistics
    stats = location_groups.aggregate(
        total_locations=Count('id'),
        total_capacity=Sum('normalized_capacity_mw')
    )
    
    # OPTIMIZED: Extract metadata from sample instead of all results
    # Use larger sample size to ensure cross-filtering completeness (dropdown coverage)
    sample_size = min(2000, location_groups.count())  # Increased from 500 to 2000 to include low-capacity companies
    sample_data = location_groups.order_by('-normalized_capacity_mw').values_list(
        'technologies', 'auction_years', 'companies'
    )[:sample_size]
    
    total_components = 0
    all_auction_years = set()
    all_companies = set()
    all_technologies = set()
    
    for techs, years, companies in sample_data:
        if techs and technology_display in techs:
            total_components += techs[technology_display]
        if years:
            all_auction_years.update(years)
        if companies:
            all_companies.update(companies.keys())
        if techs:
            all_technologies.update(techs.keys())
    
    # If sample data is insufficient, get fallback data from all LocationGroups
    if len(all_auction_years) < 3 or len(all_companies) < 5:
        logger.info(f"Sample insufficient (years: {len(all_auction_years)}, companies: {len(all_companies)}), using fallback data")
        fallback_data = LocationGroup.objects.filter(
            is_active=True
        ).values_list('auction_years', 'companies', 'technologies')[:100]
        
        for years, comps, techs in fallback_data:
            if years:
                all_auction_years.update(years)
            if comps:
                all_companies.update(comps.keys())
            if techs:
                all_technologies.update(techs.keys())
    
    # If we need exact component count and didn't get it from sample, use aggregation
    if total_components == 0:
        # Use database aggregation as fallback
        total_components = stats['total_locations'] or 0  # Approximate as location count
    
    # OPTIMIZED: Select only needed fields and paginate BEFORE processing
    display_fields = location_groups.only(
        'id',                       # Required for URL generation
        'location',                 # Displayed as title
        'component_count',          # Displayed as count
        'descriptions',             # Displayed as description text
        'technologies',             # Displayed as technology badges
        'normalized_capacity_mw'    # Displayed as capacity
    )
    
    # Paginate only if we have results
    if display_fields.exists():
        paginator = Paginator(display_fields, per_page)
        try:
            page_obj = paginator.page(page)
        except:
            page_obj = paginator.page(1)
    else:
        # Create empty page object
        from django.core.paginator import Page
        paginator = Paginator([], 1)
        page_obj = Page([], 1, paginator)
    
    # Sort auction years (newest first)
    def get_year_key(year_str):
        import re
        match = re.search(r'(\d{4})-\d{2}', year_str)
        if match:
            return int(match.group(1))
        return 0
    
    sorted_auction_years = sorted(all_auction_years, key=get_year_key, reverse=True)
    companies = sorted(list(all_companies))
    technologies = sorted(list(all_technologies))
    
    # Get the color for this technology
    tech_color = technology_color(technology_display)
    
    
    # Build context
    context = {
        'technology_name': technology_display,
        'technology_color': tech_color,
        'location_groups': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_locations': stats['total_locations'] or 0,
        'total_capacity': stats['total_capacity'] or 0,
        'total_components': total_components,
        'total_companies': 0,  # Not calculated anymore for performance
        'auction_years': sorted_auction_years,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'companies': companies,  # NEW: Company filter dropdown
        'company_filter': company_filter,  # NEW: Selected company filter
        'technologies': technologies,  # Add technologies for cross-filtering
        'technology_filter': '',  # No technology filter in technology view
        'per_page': per_page,
        'page': page,
        'api_time': time.time() - start_time,
    }
    
    logger.info(f"Optimized technology view for '{technology_display}': "
                f"{stats['total_locations']} locations in "
                f"{context['api_time']:.2f}s")
    
    return render(request, 'checker/technology_detail_optimized.html', context)


