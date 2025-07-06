"""
Optimized technology views using LocationGroup model and proper indexing.
This replaces the slow Component-based queries with fast LocationGroup queries.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
import time
import logging

from checker.models import LocationGroup, Component

logger = logging.getLogger(__name__)

def technology_map_optimized(request, technology=None):
    """
    Optimized technology map view using LocationGroup model.
    ~10x faster than Component-based queries.
    """
    start_time = time.time()
    
    if not technology:
        technology = request.GET.get('technology', 'Battery')
    
    # Normalize technology for consistent caching
    technology_normalized = technology.strip().title()
    
    # Try cache first (cache-safe key)
    import re
    safe_tech_name = re.sub(r'[^a-zA-Z0-9_]', '_', technology_normalized.upper())
    cache_key = f"tech_map_{safe_tech_name}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"Using cached data for {technology} (cache hit)")
        cached_data['from_cache'] = True
        cached_data['query_time'] = 0
        return render(request, 'checker/technology_map.html', cached_data)
    
    # Query LocationGroups instead of Components
    # This uses the GIN index on technologies JSONB field
    query_start = time.time()
    
    location_groups = LocationGroup.objects.filter(
        technologies__icontains=technology_normalized
    ).exclude(
        latitude__isnull=True
    ).exclude(
        longitude__isnull=True
    )
    
    # Get summary statistics efficiently
    total_locations = location_groups.count()
    
    # Aggregate capacity and component counts
    aggregates = location_groups.aggregate(
        total_capacity=Sum('normalized_capacity_mw'),
        total_components=Sum('component_count')
    )
    
    # Get unique companies and years from JSONB fields
    all_companies = set()
    all_years = set()
    
    for lg in location_groups.only('companies', 'auction_years'):
        if lg.companies:
            all_companies.update(lg.companies)
        if lg.auction_years:
            all_years.update(lg.auction_years)
    
    # Prepare map data - only fetch needed fields
    map_locations = location_groups.values(
        'id', 'location', 'latitude', 'longitude', 
        'normalized_capacity_mw', 'component_count', 'technologies'
    )
    
    query_time = time.time() - query_start
    
    # Build context
    context = {
        'technology': technology_normalized,
        'total_locations': total_locations,
        'total_capacity': aggregates['total_capacity'] or 0,
        'total_components': aggregates['total_components'] or 0,
        'company_count': len(all_companies),
        'year_count': len(all_years),
        'companies': sorted(list(all_companies))[:20],  # Limit for display
        'years': sorted(list(all_years), reverse=True)[:10],
        'map_locations': list(map_locations),
        'query_time': query_time,
        'from_cache': False,
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, context, 1800)
    
    total_time = time.time() - start_time
    logger.info(f"Technology {technology} loaded in {total_time:.3f}s ({query_time:.3f}s query)")
    
    return render(request, 'checker/technology_map.html', context)

def technology_list_optimized(request, technology=None):
    """
    Optimized technology list view with pagination using LocationGroup.
    Much faster than Component-based listing.
    """
    start_time = time.time()
    
    if not technology:
        technology = request.GET.get('technology', 'Battery')
    
    technology_normalized = technology.strip().title()
    page_number = request.GET.get('page', 1)
    per_page = int(request.GET.get('per_page', 25))
    sort_field = request.GET.get('sort', 'location')
    sort_order = request.GET.get('order', 'asc')
    
    # Build cache key including pagination (cache-safe)
    import re
    safe_tech_name = re.sub(r'[^a-zA-Z0-9_]', '_', technology_normalized.upper())
    cache_key = f"tech_list_{safe_tech_name}_{page_number}_{per_page}_{sort_field}_{sort_order}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"Using cached list for {technology} page {page_number}")
        return render(request, 'checker/technology_list.html', cached_data)
    
    # Query LocationGroups with proper sorting
    query_start = time.time()
    
    location_groups = LocationGroup.objects.filter(
        technologies__icontains=technology_normalized
    )
    
    # Apply sorting
    sort_prefix = '-' if sort_order == 'desc' else ''
    if sort_field == 'capacity':
        location_groups = location_groups.order_by(f'{sort_prefix}normalized_capacity_mw')
    elif sort_field == 'components':
        location_groups = location_groups.order_by(f'{sort_prefix}component_count')
    else:  # Default to location
        location_groups = location_groups.order_by(f'{sort_prefix}location')
    
    # Paginate
    paginator = Paginator(location_groups, per_page)
    page_obj = paginator.get_page(page_number)
    
    query_time = time.time() - query_start
    
    context = {
        'technology': technology_normalized,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': paginator.count,
        'sort_field': sort_field,
        'sort_order': sort_order,
        'per_page': per_page,
        'query_time': query_time,
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, context, 900)
    
    total_time = time.time() - start_time
    logger.info(f"Technology list {technology} page {page_number} loaded in {total_time:.3f}s")
    
    return render(request, 'checker/technology_list.html', context)

def technology_api_optimized(request):
    """
    Optimized API endpoint for technology data.
    Returns aggregated data much faster than Component queries.
    """
    technology = request.GET.get('technology', 'Battery')
    format_type = request.GET.get('format', 'summary')  # 'summary' or 'locations'
    
    technology_normalized = technology.strip().title()
    
    # Cache key based on parameters (cache-safe)
    import re
    safe_tech_name = re.sub(r'[^a-zA-Z0-9_]', '_', technology_normalized.upper())
    cache_key = f"tech_api_{safe_tech_name}_{format_type}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
    
    start_time = time.time()
    
    if format_type == 'summary':
        # Return summary statistics
        location_groups = LocationGroup.objects.filter(
            technologies__icontains=technology_normalized
        )
        
        aggregates = location_groups.aggregate(
            total_locations=Count('id'),
            total_capacity=Sum('normalized_capacity_mw'),
            total_components=Sum('component_count')
        )
        
        # Get unique companies efficiently
        all_companies = set()
        for lg in location_groups.only('companies'):
            if lg.companies:
                all_companies.update(lg.companies)
        
        response_data = {
            'technology': technology_normalized,
            'statistics': {
                'locations': aggregates['total_locations'],
                'capacity_mw': float(aggregates['total_capacity'] or 0),
                'components': aggregates['total_components'],
                'companies': len(all_companies)
            },
            'top_companies': sorted(list(all_companies))[:10],
            'query_time': time.time() - start_time
        }
    
    elif format_type == 'locations':
        # Return location data for maps
        locations = LocationGroup.objects.filter(
            technologies__icontains=technology_normalized,
            latitude__isnull=False,
            longitude__isnull=False
        ).values(
            'location', 'latitude', 'longitude', 
            'normalized_capacity_mw', 'component_count'
        )
        
        response_data = {
            'technology': technology_normalized,
            'locations': list(locations),
            'count': len(locations),
            'query_time': time.time() - start_time
        }
    
    else:
        response_data = {'error': 'Invalid format parameter'}
    
    # Cache for 20 minutes
    cache.set(cache_key, response_data, 1200)
    
    return JsonResponse(response_data)

def compare_query_performance(request):
    """
    Development endpoint to compare old vs new query performance.
    Remove this in production.
    """
    technology = request.GET.get('technology', 'DSR')
    
    results = {}
    
    # Test old Component-based approach
    start = time.time()
    old_count = Component.objects.filter(technology__icontains=technology).count()
    old_time = time.time() - start
    
    # Test new LocationGroup approach
    start = time.time()
    new_count = LocationGroup.objects.filter(technologies__icontains=technology).count()
    new_time = time.time() - start
    
    # Test exact match (fastest)
    start = time.time()
    exact_count = LocationGroup.objects.filter(technologies__contains=[technology]).count()
    exact_time = time.time() - start
    
    results = {
        'technology': technology,
        'old_approach': {
            'method': 'Component.objects.filter(technology__icontains=...)',
            'time': f"{old_time:.4f}s",
            'count': old_count
        },
        'new_approach': {
            'method': 'LocationGroup.objects.filter(technologies__icontains=...)',
            'time': f"{new_time:.4f}s", 
            'count': new_count
        },
        'exact_match': {
            'method': 'LocationGroup.objects.filter(technologies__contains=...)',
            'time': f"{exact_time:.4f}s",
            'count': exact_count
        },
        'improvement': f"{old_time/new_time:.1f}x faster" if new_time > 0 else "N/A"
    }
    
    return JsonResponse(results, json_dumps_params={'indent': 2})

# Example of how to integrate this into your existing views.py
INTEGRATION_EXAMPLE = """
# In your main views.py, replace slow technology views with:

def technology_page(request, technology):
    # Replace this slow version:
    # components = Component.objects.filter(technology__icontains=technology)
    
    # With this fast version:
    from .optimize_technology_views import technology_map_optimized
    return technology_map_optimized(request, technology)

# Or import and use the optimized functions directly:
from .optimize_technology_views import (
    technology_map_optimized, 
    technology_list_optimized,
    technology_api_optimized
)
"""