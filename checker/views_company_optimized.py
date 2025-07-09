"""
Optimized company detail view using LocationGroup for high performance
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
from .utils import normalize, deslugify
from .decorators.access_required import map_access_required
from .decorators.bot_protection import bot_protected_view
from .structured_data import generate_company_structured_data

logger = logging.getLogger(__name__)


@bot_protected_view(rate='5/m')  # Strict rate limiting for bots
def company_detail_optimized(request, company_id):
    """
    Optimized company detail view using LocationGroup
    Shows all locations where this company has components
    """
    start_time = time.time()
    
    # MONITORING: Count database queries
    from django.db import connection
    queries_before = len(connection.queries)
    
    # SIMPLIFIED: Just use the normalize function in reverse to find the actual company name
    normalized_name = company_id
    
    # Find the actual company name by looking up in Component table with better matching
    sample_component = Component.objects.filter(
        company_name__isnull=False
    ).extra(
        where=["LOWER(REGEXP_REPLACE(company_name, '[^a-zA-Z0-9]', '', 'g')) = %s"],
        params=[normalized_name.lower()]
    ).first()
    
    if sample_component:
        actual_company_name = sample_component.company_name
        display_name = actual_company_name
        location_groups = LocationGroup.objects.filter(
            companies__has_key=actual_company_name
        )
        logger.info(f"Found company '{actual_company_name}' with {location_groups.count()} locations")
    else:
        # Fallback: try to find any company that matches when normalized
        logger.warning(f"Direct match failed, searching all companies for '{normalized_name}'")
        
        # Get all unique company names and check each one
        all_companies = Component.objects.values_list('company_name', flat=True).distinct()
        
        for company_name in all_companies:
            if company_name and normalize(company_name) == normalized_name:
                actual_company_name = company_name
                display_name = company_name
                location_groups = LocationGroup.objects.filter(
                    companies__has_key=company_name
                )
                logger.info(f"Found company '{actual_company_name}' via normalization check")
                break
        
        if not actual_company_name:
            logger.warning(f"Company '{normalized_name}' not found anywhere")
            actual_company_name = normalized_name
            display_name = normalized_name.title()
            location_groups = LocationGroup.objects.none()
    
    # Get parameters
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    sort_by = request.GET.get('sort_by', 'capacity')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', 'all')
    technology_filter = request.GET.get('technology', 'all')  # NEW: Technology filtering
    
    
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
    
    # OPTIMIZED: Apply technology filter at database level (NEW HIERARCHY FEATURE!)
    if technology_filter != 'all':
        location_groups = location_groups.filter(
            technologies__has_key=technology_filter
        )
    
    # Apply sorting
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'components':
        order_field = 'component_count'
    elif sort_by == 'date':
        # Sort by the latest auction year (using auction_years JSON field)
        order_field = 'auction_years__0'  # First element of the array (should be latest)
    else:  # Default to capacity
        order_field = 'normalized_capacity_mw'
    
    if sort_order == 'desc' and order_field not in ['location']:
        order_field = f'-{order_field}'
    elif sort_order == 'asc' and order_field == 'location':
        # Location should be A-Z by default
        pass
    elif sort_order == 'desc' and order_field == 'location':
        order_field = '-location'
    
    location_groups = location_groups.order_by(order_field)
    
    # Calculate company-wide statistics
    stats = location_groups.aggregate(
        total_locations=Count('id'),
        total_capacity=Sum('normalized_capacity_mw')
    )
    
    # OPTIMIZED: Extract metadata from a sample instead of all results
    # This prevents loading all LocationGroups into memory
    # Use larger sample size to ensure cross-filtering completeness (dropdown coverage)
    # PERFORMANCE: Use lazy loading for filters - load via AJAX on dropdown interaction
    filter_start = time.time()
    
    # Show dropdowns with placeholder content - populated by AJAX when clicked
    all_technologies = ['Loading...']
    all_auction_years = ['Loading...']
    total_components = 0  # Will be calculated separately if needed
    
    timings = {'lazy_filters': time.time() - filter_start}
    logger.info("🚀 Company view using lazy loading - filters will load on dropdown interaction")
    
    # If we need exact component count and didn't get it from sample, use aggregation
    if total_components == 0 and actual_company_name:
        # Use database aggregation to get total component count efficiently
        component_sum = location_groups.aggregate(
            total=Sum('component_count')
        )
        total_components = component_sum['total'] or 0
    
    # OPTIMIZED: Select only fields needed for display (reduces row size by ~70%)
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
    
    # Generate structured data for SEO
    class CompanyData:
        def __init__(self, total_capacity):
            self.total_capacity = total_capacity
    
    company_data = CompanyData(stats['total_capacity'] or 0)
    structured_data = generate_company_structured_data(display_name, company_data, request)
    
    # Build context
    context = {
        'company_id': company_id,  # Keep original for URL consistency
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
        'technology_filter': technology_filter,  # NEW: Pass technology filter to template
        'per_page': per_page,
        'page': page,
        'api_time': time.time() - start_time,
        'structured_data': structured_data,  # SEO structured data
    }
    
    # MONITORING: Calculate optimization metrics
    queries_after = len(connection.queries)
    query_count = queries_after - queries_before
    
    # Calculate data transfer estimate
    if page_obj:
        rows_fetched = len(page_obj)  # Only page data with lazy loading
        estimated_bytes = rows_fetched * 6 * 50  # 6 fields * ~50 bytes per field
    else:
        rows_fetched = 0
        estimated_bytes = 0
    
    # Enhanced logging with optimization metrics
    logger.info(f"🚀 EGRESS-OPTIMIZED company view for '{display_name}':")
    logger.info(f"   📊 Total locations: {stats['total_locations']}")
    logger.info(f"   📋 Displayed: {len(page_obj)} items (page {page})")
    logger.info(f"   🔍 Using lazy loading - no metadata sampling")
    logger.info(f"   💾 Database queries: {query_count}")
    logger.info(f"   📦 Rows fetched: {rows_fetched}")
    logger.info(f"   📊 Estimated data: {estimated_bytes:,} bytes ({estimated_bytes/1024:.1f} KB)")
    logger.info(f"   ⏱️  Load time: {context['api_time']:.3f}s")
    logger.info(f"   🔧 Filters: status={status_filter}, auction={auction_filter}, technology={technology_filter}")
    
    # Compare to old approach estimate
    if stats['total_locations']:
        old_estimate = stats['total_locations'] * 24 * 50  # All fields, all locations
        reduction = ((old_estimate - estimated_bytes) / old_estimate) * 100
        logger.info(f"   💡 Estimated egress reduction: {reduction:.1f}% ({old_estimate:,} → {estimated_bytes:,} bytes)")
    
    return render(request, 'checker/company_detail_optimized.html', context)


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
def company_detail_map(request, company_name=None, company_slug=None):
    """
    Map view for company locations - similar to technology map view
    Shows all locations for a specific company on an interactive map
    """
    start_time = time.time()
    
    # MONITORING: Count database queries
    from django.db import connection
    queries_before = len(connection.queries)
    
    # Handle both slug and legacy company_name parameters
    if company_name:
        # Check if it's a slug (lowercase with hyphens) or legacy format (uppercase with %20)
        if '%' in company_name or company_name.isupper():
            # Legacy URL-encoded format
            company_display = urllib.parse.unquote(company_name)
        else:
            # New slug format - deslugify to get display name
            company_display = deslugify(company_name)
    elif company_slug:
        # Legacy parameter name - URL decode
        company_display = urllib.parse.unquote(company_slug)
    else:
        raise ValueError("Either company_name or company_slug must be provided")
    
    # Initialize actual_company_name for consistency
    actual_company_name = company_display
    
    # Get parameters
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', '')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    technology_filter = request.GET.get('technology', '')
    
    # Company pages are filtered views, not search results - default to location sorting
    if sort_by == 'relevance':
        sort_by = 'location'
    
    # FIXED: Find the correct company name case-insensitively
    # First try exact match (for performance)
    location_groups = LocationGroup.objects.filter(
        companies__has_key=company_display
    )
    
    # If no exact match, find the correct case version
    if location_groups.count() == 0:
        # Find a location that contains this company name (case-insensitive)
        sample_location = LocationGroup.objects.filter(
            companies__icontains=company_display
        ).first()
        
        if sample_location and sample_location.companies:
            import json
            companies_dict = json.loads(sample_location.companies) if isinstance(sample_location.companies, str) else sample_location.companies
            # Find the exact key that matches (case-insensitive)
            for key in companies_dict.keys():
                if key.lower() == company_display.lower():
                    company_display = key  # Use the correct case
                    break
            
            # Re-run query with correct case
            location_groups = LocationGroup.objects.filter(
                companies__has_key=company_display
            )
    
    # Apply status filtering
    if status_filter == 'active':
        location_groups = location_groups.filter(is_active=True)
    elif status_filter == 'inactive':
        location_groups = location_groups.filter(is_active=False)
    
    # OPTIMIZED: Apply auction year filtering at database level
    if auction_filter and auction_filter != 'all':
        location_groups = location_groups.filter(
            auction_years__icontains=auction_filter
        )
    
    # Apply technology filtering
    if technology_filter and technology_filter != 'all':
        location_groups = location_groups.filter(technologies__has_key=technology_filter)
    
    # COMPANY-SPECIFIC: Get metadata only from this company's locations
    # PERFORMANCE: Use lazy loading for filters - load via AJAX on dropdown interaction
    filter_start = time.time()
    
    # Show dropdowns with placeholder content - populated by AJAX when clicked
    all_auction_years = ['Loading...']
    all_technologies = ['Loading...']
    
    timings = {'lazy_filters': time.time() - filter_start}
    logger.info("🚀 Company map view using lazy loading - filters will load on dropdown interaction")
    
    # For company-specific view, we don't need fallback data since we want only this company's data
    # This ensures filters show only technologies/years relevant to this specific company
    
    # Sort auction years
    import re
    def extract_year(year_str):
        match = re.search(r'(\d{4})', year_str)
        return int(match.group(1)) if match else 0
    
    auction_years = sorted(all_auction_years, key=extract_year, reverse=True)
    technologies = sorted(list(all_technologies))
    # No companies dropdown needed for company-specific view
    companies = []
    
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
        # Sort by first (most recent) auction year
        location_groups = location_groups.order_by(
            'auction_years__0' if sort_order == 'asc' else '-auction_years__0'
        )
    else:  # relevance (default)
        # For company view, relevance = capacity
        location_groups = location_groups.order_by('-normalized_capacity_mw')
    
    # OPTIMIZED: Select only needed fields and paginate BEFORE processing
    optimized_locations = location_groups.only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    # Pagination BEFORE creating list (key optimization!)
    paginator = Paginator(optimized_locations, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)
    
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
    
    # OPTIMIZED: Calculate totals using database aggregation
    totals = location_groups.aggregate(
        total_locations=Count('id'),
        total_capacity=Sum('normalized_capacity_mw')
    )
    
    # Get component count for this company efficiently
    total_components = location_groups.aggregate(
        total=Sum('component_count')
    )['total'] or 0
    
    
    load_time = time.time() - start_time
    
    # MONITORING: Calculate optimization metrics
    queries_after = len(connection.queries)
    query_count = queries_after - queries_before
    
    rows_fetched = len(page_obj)  # Only page data with lazy loading
    estimated_bytes = rows_fetched * 10 * 50  # 10 fields * ~50 bytes per field
    
    # Enhanced logging with optimization metrics
    logger.info(f"🗺️  EGRESS-OPTIMIZED company map for '{company_display}':")
    logger.info(f"   📊 Total locations: {totals['total_locations']}")
    logger.info(f"   📋 Displayed: {len(page_obj)} items (page {page_number})")
    logger.info(f"   🔍 Using lazy loading - no metadata sampling")
    logger.info(f"   💾 Database queries: {query_count}")
    logger.info(f"   📦 Rows fetched: {rows_fetched}")
    logger.info(f"   📊 Estimated data: {estimated_bytes:,} bytes ({estimated_bytes/1024:.1f} KB)")
    logger.info(f"   ⏱️  Load time: {load_time:.3f}s")
    
    # Compare to old approach estimate
    if totals['total_locations']:
        old_estimate = totals['total_locations'] * 24 * 50  # All fields, all locations
        reduction = ((old_estimate - estimated_bytes) / old_estimate) * 100
        logger.info(f"   💡 Estimated egress reduction: {reduction:.1f}% ({old_estimate:,} → {estimated_bytes:,} bytes)")
    
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
        'companies': companies,  # Add companies for cross-filtering
        'company_filter': 'all',  # Add missing company_filter
        'status_filter': status_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'query': request.GET.get('q', ''),  # Get query from request parameters
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    
    return render(request, 'checker/search_company_map.html', context)


