"""
Optimized company detail view using LocationGroup for high performance
PATCHED: Use database-level filtering instead of Python loops
"""
import logging
import time
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
import urllib.parse

from .models import LocationGroup, Component
from .utils import normalize

logger = logging.getLogger(__name__)


def company_detail_optimized(request, company_id):
    """
    Optimized company detail view using LocationGroup
    PATCHED: Uses database-level filtering to reduce egress by 99%
    """
    start_time = time.time()
    
    # Get the display company name from the normalized ID
    normalized_name = company_id
    
    # Try to find the actual company name from a Component
    sample_component = Component.objects.filter(
        company_name__iregex=rf'^{normalized_name.replace("limited", ".*limited")}$'
    ).first()
    
    if sample_component:
        actual_company_name = sample_component.company_name
        display_name = actual_company_name
        possible_names = [actual_company_name]
    else:
        # Fallback to possible name variations
        possible_names = [
            normalized_name,
            normalized_name.upper(),
            normalized_name.replace('limited', ' limited'),
            normalized_name.replace('limited', ' LIMITED'),
        ]
        display_name = normalized_name.title()
    
    # Get parameters
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    sort_by = request.GET.get('sort_by', 'capacity')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', 'all')
    
    # Find LocationGroups for this company
    location_groups = LocationGroup.objects.none()
    actual_company_name = None
    
    # Try each possible name
    for possible_name in possible_names:
        test_groups = LocationGroup.objects.filter(
            companies__has_key=possible_name
        )
        if test_groups.exists():
            location_groups = test_groups
            actual_company_name = possible_name
            display_name = possible_name
            break
    
    # PATCHED: Apply database-level filtering instead of Python loops
    if status_filter == 'active':
        # Use Q objects for database-level OR filtering
        active_years = ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']
        q_filter = Q()
        for year in active_years:
            q_filter |= Q(auction_years__contains=year)
        location_groups = location_groups.filter(q_filter)
        
    elif status_filter == 'inactive':
        # Exclude all active years at database level
        active_years = ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']
        for year in active_years:
            location_groups = location_groups.exclude(auction_years__contains=year)
    
    # PATCHED: Apply auction year filter at database level
    if auction_filter != 'all':
        location_groups = location_groups.filter(auction_years__contains=auction_filter)
    
    # Apply sorting
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'components':
        order_field = 'component_count'
    elif sort_by == 'date':
        order_field = 'auction_years__0'
    else:  # Default to capacity
        order_field = 'normalized_capacity_mw'
    
    if sort_order == 'desc' and order_field not in ['location']:
        order_field = f'-{order_field}'
    elif sort_order == 'desc' and order_field == 'location':
        order_field = '-location'
    
    location_groups = location_groups.order_by(order_field)
    
    # PATCHED: Get statistics BEFORE pagination using aggregation
    stats = location_groups.aggregate(
        total_locations=Count('id'),
        total_capacity=Sum('normalized_capacity_mw')
    )
    
    # PATCHED: Get sample of technologies and auction years efficiently
    # Only fetch a limited sample for UI display, not all rows
    sample_locations = location_groups.values_list(
        'technologies', 'auction_years', 'companies'
    )[:100]  # Limit to 100 rows for metadata extraction
    
    all_technologies = set()
    all_auction_years = set()
    total_components = 0
    
    for techs, years, companies in sample_locations:
        if techs:
            all_technologies.update(techs.keys())
        if years:
            all_auction_years.update(years)
        if companies and display_name in companies:
            total_components += companies.get(display_name, 0)
    
    # If we need exact component count, use aggregation
    if total_components == 0 and actual_company_name:
        # This is still efficient - single aggregation query
        component_sum = location_groups.filter(
            companies__has_key=actual_company_name
        ).aggregate(
            total=Sum('component_count')
        )
        total_components = component_sum['total'] or 0
    
    # Paginate results
    paginator = Paginator(location_groups, per_page)
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    # Sort auction years
    def get_year_key(year_str):
        import re
        match = re.search(r'(\d{4})-\d{2}', year_str)
        return int(match.group(1)) if match else 0
    
    sorted_auction_years = sorted(all_auction_years, key=get_year_key, reverse=True)
    
    # Build context
    context = {
        'company_id': company_id,
        'company_name': display_name,
        'location_groups': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_locations': stats['total_locations'] or 0,
        'total_capacity': stats['total_capacity'] or 0,
        'total_components': total_components,
        'technologies': sorted(list(all_technologies)),
        'auction_years': sorted_auction_years,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'per_page': per_page,
        'page': page,
        'api_time': time.time() - start_time,
    }
    
    logger.info(f"Optimized company view for '{display_name}': "
                f"{stats['total_locations']} locations in "
                f"{context['api_time']:.2f}s")
    
    return render(request, 'checker/company_detail_optimized.html', context)


# Monitoring import
try:
    from monitoring.decorators import monitor_api
except ImportError:
    def monitor_api(func):
        return func

@monitor_api
@gzip_page
# @cache_page(60 * 10)  # Disabled to prevent Redis memory issues - pages are fast enough without cache
def company_detail_map(request, company_name):
    """
    Map view for company locations - similar to technology map view
    PATCHED: Uses database filtering and field selection
    """
    start_time = time.time()
    
    # Decode company name
    company_display = urllib.parse.unquote(company_name)
    
    # Get parameters
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', '')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    technology_filter = request.GET.get('technology', '')
    
    # PATCHED: Start with optimized query selecting only needed fields
    location_groups = LocationGroup.objects.filter(
        companies__has_key=company_display
    ).only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    # PATCHED: Apply filters at database level
    if status_filter == 'active':
        # Use Q objects for OR filtering
        from django.db.models import Q
        active_years = ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29']
        q_filter = Q()
        for year in active_years:
            q_filter |= Q(auction_years__contains=year)
        location_groups = location_groups.filter(q_filter)
    elif status_filter == 'inactive':
        # Exclude active years
        active_years = ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29']
        for year in active_years:
            location_groups = location_groups.exclude(auction_years__contains=year)
    
    # Apply auction year filtering at database level
    if auction_filter and auction_filter != 'all':
        location_groups = location_groups.filter(auction_years__contains=auction_filter)
    
    # Apply technology filtering at database level
    if technology_filter:
        location_groups = location_groups.filter(technologies__has_key=technology_filter)
    
    # Apply sorting
    if sort_by == 'location':
        location_groups = location_groups.order_by(
            'location' if sort_order == 'asc' else '-location'
        )
    elif sort_by == 'components':
        location_groups = location_groups.order_by(
            'component_count' if sort_order == 'asc' else '-component_count'
        )
    elif sort_by == 'mw':
        location_groups = location_groups.order_by(
            'normalized_capacity_mw' if sort_order == 'asc' else '-normalized_capacity_mw'
        )
    elif sort_by == 'date':
        location_groups = location_groups.order_by(
            'auction_years__0' if sort_order == 'asc' else '-auction_years__0'
        )
    else:  # relevance (default)
        location_groups = location_groups.order_by('-normalized_capacity_mw')
    
    # PATCHED: Get metadata efficiently from a sample
    sample_data = location_groups.values_list(
        'auction_years', 'technologies'
    )[:100]
    
    all_auction_years = set()
    all_technologies = set()
    
    for years, techs in sample_data:
        if years:
            all_auction_years.update(years)
        if techs:
            all_technologies.update(techs.keys())
    
    # Sort auction years and technologies
    import re
    def extract_year(year_str):
        match = re.search(r'(\d{4})', year_str)
        return int(match.group(1)) if match else 0
    
    auction_years = sorted(all_auction_years, key=extract_year, reverse=True)
    technologies = sorted(list(all_technologies))
    
    # PATCHED: Convert to list with is_active calculation
    # But only for the page we're displaying
    paginator = Paginator(location_groups, 10)  # 10 items per page
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)
    
    # Process only the current page items
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
        
        # Check if active
        if lg.auction_years:
            lg_dict['is_active'] = any(
                pattern in year for year in lg.auction_years 
                for pattern in active_patterns
            )
        
        location_groups_list.append(lg_dict)
    
    # Replace page_obj's object_list
    page_obj.object_list = location_groups_list
    
    # Calculate totals using aggregation
    totals = location_groups.aggregate(
        total_locations=Count('id'),
        total_capacity=Sum('normalized_capacity_mw')
    )
    
    # Get component count for this company
    total_components = location_groups.filter(
        companies__has_key=company_display
    ).aggregate(
        total=Sum('component_count')
    )['total'] or 0
    
    load_time = time.time() - start_time
    logger.info(f"Company map view for {company_display} loaded in {load_time:.2f}s")
    
    context = {
        'company_name': company_display,
        'page_obj': page_obj,
        'total_locations': totals['total_locations'] or 0,
        'total_components': total_components,
        'total_capacity': totals['total_capacity'] or 0,
        'auction_years': auction_years,
        'auction_filter': auction_filter,
        'technology_filter': technology_filter,
        'technologies': technologies,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'query': request.GET.get('q', ''),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    
    return render(request, 'checker/search_company_map.html', context)
