"""
Optimized component search service v2 with better performance for location searches
"""
import logging
import time
import hashlib
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from django.db import connection
from django.core.cache import cache

from ..models import LocationGroup, Component
from .postcode_helpers import get_all_postcodes_for_area
from .search_suggestions import get_multiple_suggestions, get_did_you_mean_suggestion
from ..decorators.access_required import access_required

logger = logging.getLogger(__name__)


@access_required
def search_components_optimized_v2(request):
    """
    Optimized search v2 with better handling of postcode searches
    and re-enabled company search
    """
    start_time = time.time()
    
    # Get search parameters - support both 'q' and 'query'
    query = request.GET.get('query', request.GET.get('q', '')).strip()
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    
    # Create cache key for search results
    cache_params = f"{query}:{page}:{per_page}:{sort_by}:{sort_order}:{status_filter}:{auction_filter}"
    cache_key = f"search_results_v2:{hashlib.md5(cache_params.encode()).hexdigest()}"
    
    # Check cache first (5 minute TTL for search results)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache HIT for search '{query}' (page {page}) - returning cached result")
        cached_result['cache_hit'] = True
        cached_result['cache_key'] = cache_key
        return cached_result
    
    logger.info(f"Cache MISS for search '{query}' (page {page}) - performing search")
    
    # Initialize timing
    timings = {}
    
    # Search for companies directly in the database
    company_start = time.time()
    company_links = []
    if query:
        try:
            # Use raw SQL to search company names in LocationGroup's JSON field
            # This is much faster than Redis for ~1600 companies
            
            with connection.cursor() as cursor:
                # Get unique companies matching the query with their total component counts
                cursor.execute("""
                    SELECT company_name, SUM(component_count) as total_components
                    FROM (
                        SELECT jsonb_object_keys(companies) as company_name,
                               (companies->jsonb_object_keys(companies))::int as component_count
                        FROM checker_locationgroup
                        WHERE companies IS NOT NULL
                    ) as company_data
                    WHERE LOWER(company_name) LIKE %s
                    GROUP BY company_name
                    ORDER BY total_components DESC
                    LIMIT 10
                """, [f'%{query.lower()}%'])
                
                companies = []
                for row in cursor.fetchall():
                    companies.append({
                        'company_name': row[0],
                        'component_count': row[1]
                    })
            
            company_links = []
            for company in companies:
                # Normalize company name for URL
                company_id = company['company_name'].lower().replace(' ', '').replace('(', '').replace(')', '').replace('-', '').replace('.', '')
                company_links.append({
                    'html': f'''
                        <div>
                            <strong><a href="/company-optimized/{company_id}/">{company['company_name']}</a></strong>
                            <div class="mt-1 mb-1"><span class="text-muted">{company['component_count']} components</span></div>
                        </div>
                    '''
                })
            
            logger.info(f"Database company search found {len(companies)} matches in {time.time() - company_start:.3f}s")
            
        except Exception as e:
            logger.error(f"Company search error: {e}")
            company_links = []
    
    timings['company_search'] = time.time() - company_start
    logger.info(f"Found {len(company_links)} company links for query '{query}'")
    
    # Use LocationGroup search
    location_search_start = time.time()
    
    if query:
        logger.info(f"=== OPTIMIZED SEARCH V2: Processing query '{query}' ===")
        # Check if it's likely a postcode search
        query_upper = query.upper()
        is_postcode_search = (
            len(query_upper) <= 4 and 
            query_upper[:2].isalpha() and 
            any(c.isdigit() for c in query_upper)
        )
        
        if is_postcode_search:
            # Direct postcode search is much faster
            location_groups = LocationGroup.objects.filter(
                Q(outward_code__iexact=query_upper) |
                Q(outward_code__istartswith=query_upper)
            )
        else:
            # Handle multi-word queries by splitting and requiring ALL words to match
            query_parts = query.split()
            
            if len(query_parts) > 1:
                # Multi-word search: each word must match somewhere in the component
                component_filter = Q()
                for part in query_parts:
                    part_filter = (
                        Q(location__icontains=part) |
                        Q(company_name__icontains=part) |
                        Q(description__icontains=part) |
                        Q(cmu_id__icontains=part) |
                        Q(technology__icontains=part) |
                        Q(county__icontains=part)
                    )
                    component_filter &= part_filter  # AND logic - all parts must match
                
                # Find unique locations that have matching components
                matching_locations = Component.objects.filter(
                    component_filter
                ).values_list('location', flat=True).distinct()
                
                logger.info(f"Multi-word search '{query}': found {len(matching_locations)} matching locations")
                
                # Get LocationGroups for these locations
                location_groups = LocationGroup.objects.filter(location__in=matching_locations)
            else:
                # Single word search - use LocationGroup search with proper JSON field queries
                from django.db.models import Func, F
                from django.contrib.postgres.search import SearchQuery, SearchVector
                
                # First try direct LocationGroup search with optimized JSON queries
                
                # Build optimized JSON searches
                json_filters = []
                
                # Search in company names (JSON dict keys) - use has_key for exact matches, icontains for partial
                if len(query) >= 3:  # Only do expensive text search for longer queries
                    json_filters.extend([
                        Q(companies__has_key=query),  # Exact company name match (uses GIN index)
                        Q(technologies__has_key=query),  # Exact technology match (uses GIN index)
                        Q(descriptions__contains=[query]),  # Exact description match in array
                        Q(cmu_ids__contains=[query]),  # Exact CMU ID match in array
                    ])
                
                # For partial matches, fall back to text search but only on shorter queries to avoid performance issues
                if len(query) <= 10:  # Limit expensive text operations
                    json_filters.extend([
                        Q(companies__icontains=query),  # Partial company name search
                        Q(technologies__icontains=query),  # Partial technology search
                        Q(descriptions__icontains=query),  # Partial description search
                        Q(cmu_ids__icontains=query),  # Partial CMU ID search
                    ])
                
                # Combine all filters
                base_filters = Q(location__icontains=query) | Q(county__icontains=query)
                
                # Add JSON filters to base filters
                for json_filter in json_filters:
                    base_filters |= json_filter
                
                location_groups = LocationGroup.objects.filter(base_filters)
                
                # Check if it's a postcode-based search (area/county name)
                area_postcodes = get_all_postcodes_for_area(query)
                if area_postcodes:
                    logger.info(f"Area search for '{query}' found {len(area_postcodes)} postcodes: {area_postcodes}")
                    # Search LocationGroups in those postcodes
                    postcode_filter = Q()
                    for postcode in area_postcodes:
                        postcode_filter |= Q(outward_code=postcode)
                    
                    # Combine with direct search results
                    area_groups = LocationGroup.objects.filter(postcode_filter)
                    location_groups = location_groups | area_groups
                    location_groups = location_groups.distinct()
                
                logger.info(f"LocationGroup search for '{query}' found {location_groups.count()} results")
                
                # Only do expensive Component search if we have very few results
                if location_groups.count() < 3:
                    logger.info(f"Few results, falling back to Component search")
                    # Build component filter
                    component_filter = (
                        Q(location__icontains=query) |
                        Q(company_name__icontains=query) |
                        Q(description__icontains=query) |
                        Q(cmu_id__icontains=query) |
                        Q(technology__icontains=query)
                    )
                    
                    # Add postcode filters if we have them
                    if area_postcodes:
                        postcode_filters = Q()
                        for postcode in area_postcodes:
                            postcode_filters |= Q(outward_code=postcode)
                        component_filter |= postcode_filters
                    
                    # Find unique locations (with limit for performance)
                    matching_locations = Component.objects.filter(
                        component_filter
                    ).values_list('location', flat=True).distinct()[:100]  # Limit to 100 locations
                    
                    # Get LocationGroups for these locations
                    component_groups = LocationGroup.objects.filter(location__in=matching_locations)
                    # Combine the querysets properly
                    if location_groups.exists():
                        # Get IDs from both querysets and create a new queryset
                        all_ids = list(location_groups.values_list('id', flat=True)) + list(component_groups.values_list('id', flat=True))
                        location_groups = LocationGroup.objects.filter(id__in=all_ids).distinct()
                    else:
                        location_groups = component_groups
            
            # Multi-word searches avoid the expensive postcode expansion that causes timeouts
    else:
        # No query - get all LocationGroups
        location_groups = LocationGroup.objects.all()
    
    # Apply status filter (Active/Inactive/All)
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
    
    # Apply sorting - map UI sort fields to database fields
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'mw':  # MW ↓ button
        order_field = 'normalized_capacity_mw'
    elif sort_by == 'components':
        order_field = 'component_count'
    elif sort_by == 'date':
        # Sort by most recent auction year - for now, use location as fallback
        # TODO: Implement proper date sorting based on auction years
        order_field = 'location'
    else:
        # Default to location for now
        order_field = 'location'
    
    # Handle sort order
    if sort_order == 'desc':
        if order_field == 'location':
            # For location, desc means Z-A
            order_field = f'-{order_field}'
    else:  # asc
        if order_field != 'location':
            # For non-location fields, asc means oldest/lowest first
            order_field = f'-{order_field}'
    
    location_groups = location_groups.order_by(order_field)
    
    timings['location_search'] = time.time() - location_search_start
    
    # Paginate the LocationGroup queryset directly
    pagination_start = time.time()
    paginator = Paginator(location_groups, per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    timings['pagination'] = time.time() - pagination_start
    
    # Calculate total component count more efficiently using aggregation
    count_start = time.time()
    from django.db.models import Sum
    total_components = location_groups.aggregate(total=Sum('component_count'))['total'] or 0
    timings['component_count'] = time.time() - count_start
    
    # Gather auction years for the dropdown
    all_auction_years = set()
    for lg in location_groups:
        if lg.auction_years:
            all_auction_years.update(lg.auction_years)
    auction_years = sorted(list(all_auction_years))
    
    # Check if we should show search suggestions (no results found)
    search_suggestions = []
    did_you_mean = None
    
    if query and total_components == 0 and len(company_links) == 0:
        # No results found, get search suggestions
        try:
            suggestions = get_multiple_suggestions(query)
            if suggestions:
                search_suggestions = suggestions[:3]  # Limit to 3 suggestions
                did_you_mean = suggestions[0] if suggestions else None
                logger.info(f"Generated search suggestions for '{query}': {suggestions}")
        except Exception as e:
            logger.error(f"Error generating search suggestions for '{query}': {e}")
    
    # Build context
    context = {
        'query': query,
        'page_obj': page_obj,
        'company_links': company_links,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'total_components': total_components,
        'total_locations': paginator.count,
        'locations_on_page': len(page_obj.object_list),
        'api_time': time.time() - start_time,
        'timings': timings,
        'page': page,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'auction_years': auction_years,
        'search_suggestions': search_suggestions,
        'did_you_mean': did_you_mean,
    }
    
    # Log performance
    logger.info(f"Optimized search v2 for '{query}' completed in {context['api_time']:.2f}s")
    logger.info(f"Timings: {timings}")
    
    # Log query count for debugging
    logger.info(f"Database queries: {len(connection.queries)}")
    
    # Cache the result for 5 minutes (300 seconds) to speed up repeated searches
    context['cache_hit'] = False
    context['cache_key'] = cache_key
    
    # Only cache successful searches (with results)
    if context['total_locations'] > 0:
        cache.set(cache_key, context, 300)  # 5 minutes
        logger.info(f"Cached search results for '{query}' (page {page}) - {context['total_locations']} locations")
    
    # Use the optimized template
    return render(request, 'checker/search_locationgroup_optimized.html', context)