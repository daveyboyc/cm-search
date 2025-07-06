"""
Optimized CMU detail view using LocationGroup for high performance
"""
import logging
import time
import re
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count

from .models import LocationGroup, CMURegistry

logger = logging.getLogger(__name__)


def cmu_detail_optimized(request, cmu_id):
    """
    Optimized CMU detail view using LocationGroup
    Shows all locations that are part of this CMU
    """
    start_time = time.time()
    
    # Get parameters
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    sort_by = request.GET.get('sort_by', 'capacity')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    
    # Normalize CMU ID for database lookup
    # Strip 'cmu_' prefix if present and convert to uppercase
    normalized_cmu_id = cmu_id
    if normalized_cmu_id.lower().startswith('cmu_'):
        normalized_cmu_id = normalized_cmu_id[4:]  # Remove 'cmu_' prefix
    normalized_cmu_id = normalized_cmu_id.upper()
    
    # Get CMU Registry info (try both original and normalized)
    cmu_registry = CMURegistry.objects.filter(
        Q(cmu_id=cmu_id) | Q(cmu_id=normalized_cmu_id)
    ).first()
    cmu_data = {}
    if cmu_registry and isinstance(cmu_registry.raw_data, dict):
        cmu_data = cmu_registry.raw_data
    
    # Find all LocationGroups that contain this CMU
    # Since cmu_ids is a JSON array field, we need to check if the CMU ID is in the array
    # Use JSONField array containment check - this works for arrays
    from django.contrib.postgres.fields import JSONField
    location_groups = LocationGroup.objects.filter(
        cmu_ids__contains=[normalized_cmu_id]
    )
    
    # If no results with normalized ID, try with original ID  
    if not location_groups.exists() and normalized_cmu_id != cmu_id:
        location_groups = LocationGroup.objects.filter(
            cmu_ids__contains=[cmu_id.upper()]
        )
    
    # Apply status filter
    if status_filter == 'active':
        # Filter for locations with any auction year >= 2024-25
        filtered_ids = []
        for lg in location_groups:
            if lg.auction_years:
                is_active = False
                for year_str in lg.auction_years:
                    if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                        is_active = True
                        break
                if is_active:
                    filtered_ids.append(lg.id)
        location_groups = location_groups.filter(id__in=filtered_ids)
    elif status_filter == 'inactive':
        # Filter for locations with NO auction years >= 2024-25
        filtered_ids = []
        for lg in location_groups:
            if lg.auction_years:
                is_active = False
                for year_str in lg.auction_years:
                    if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                        is_active = True
                        break
                if not is_active:
                    filtered_ids.append(lg.id)
        location_groups = location_groups.filter(id__in=filtered_ids)
    
    # Apply auction year filter
    if auction_filter:
        filtered_ids = []
        for lg in location_groups:
            if lg.auction_years and auction_filter in lg.auction_years:
                filtered_ids.append(lg.id)
        location_groups = location_groups.filter(id__in=filtered_ids)
    
    # Apply sorting
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'components':
        order_field = 'component_count'
    elif sort_by == 'date':
        # For date sorting, we need to handle it manually since it's JSON data
        # Get all location groups and sort by most recent auction year
        location_groups_list = list(location_groups)
        
        def get_latest_auction_year(lg):
            if not lg.auction_years:
                return 0
            years = []
            for year_str in lg.auction_years:
                match = re.search(r'(\d{4})-\d{2}', year_str)
                if match:
                    years.append(int(match.group(1)))
            return max(years) if years else 0
        
        location_groups_list.sort(
            key=get_latest_auction_year, 
            reverse=(sort_order == 'desc')
        )
        
        # Convert back to list for pagination
        location_groups = location_groups_list
        
    else:  # Default to capacity
        order_field = 'normalized_capacity_mw'
    
    # Apply regular database sorting (skip if we did manual date sorting)
    if sort_by != 'date':
        if sort_order == 'desc' and order_field not in ['location']:
            order_field = f'-{order_field}'
        elif sort_order == 'asc' and order_field == 'location':
            pass
        elif sort_order == 'desc' and order_field == 'location':
            order_field = '-location'
        
        location_groups = location_groups.order_by(order_field)
    
    # Calculate CMU-wide statistics
    if sort_by == 'date':
        # For manual sorting, calculate stats from the list
        stats = {
            'total_locations': len(location_groups),
            'total_capacity': sum(lg.normalized_capacity_mw or 0 for lg in location_groups),
            'total_components': sum(lg.component_count or 0 for lg in location_groups)
        }
    else:
        stats = location_groups.aggregate(
            total_locations=Count('id'),
            total_capacity=Sum('normalized_capacity_mw'),
            total_components=Sum('component_count')
        )
    
    # Gather all technologies and companies
    all_technologies = set()
    all_companies = set()
    all_auction_years = set()
    location_groups_iter = location_groups if sort_by == 'date' else location_groups
    for lg in location_groups_iter:
        if lg.technologies:
            all_technologies.update(lg.technologies.keys())
        if lg.companies:
            all_companies.update(lg.companies.keys())
        if lg.auction_years:
            all_auction_years.update(lg.auction_years)
    
    # Paginate only if we have results
    if (sort_by == 'date' and location_groups) or (sort_by != 'date' and location_groups.exists()):
        paginator = Paginator(location_groups, per_page)
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
    
    # Build context
    context = {
        'cmu_id': cmu_id,  # Keep original for URL
        'normalized_cmu_id': normalized_cmu_id,  # For display
        'cmu_data': cmu_data,
        'cmu_name': cmu_data.get('CMU Name', normalized_cmu_id),
        'location_groups': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_locations': stats['total_locations'] or 0,
        'total_capacity': stats['total_capacity'] or 0,
        'total_components': stats['total_components'] or 0,
        'total_technologies': len(all_technologies),
        'total_companies': len(all_companies),
        'technologies': sorted(list(all_technologies)),
        'auction_years': sorted_auction_years,  # Show all for dropdown
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'page': page,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'api_time': time.time() - start_time,
    }
    
    logger.info(f"Optimized CMU view for '{normalized_cmu_id}' (from '{cmu_id}'): "
                f"{stats['total_locations']} locations in "
                f"{context['api_time']:.2f}s")
    
    return render(request, 'checker/cmu_detail_optimized.html', context)