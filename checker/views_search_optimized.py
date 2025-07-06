"""
Optimized search view using LocationGroup for maximum performance
Replaces the old Component-based search with egress-optimized LocationGroup search
"""
import logging
import time
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db import connection
from django.conf import settings

from .models import LocationGroup, Component
from .services.postcode_helpers import get_all_postcodes_for_area
from .services.filter_options import get_complete_filter_options
from .utils import normalize
from .decorators.access_required import access_required

logger = logging.getLogger(__name__)

@access_required
def homepage_view(request):
    """
    Homepage view - displays the main search interface
    """
    # Check if there are any search-related parameters
    search_params = ['q', 'query', 'per_page', 'sort_by', 'sort_order', 'status', 'auction', 'technology', 'page']
    has_search_params = any(param in request.GET for param in search_params)
    
    # If there are search parameters, redirect to search results (even with empty query)
    if has_search_params:
        from django.shortcuts import redirect
        from urllib.parse import urlencode
        from .access_control import get_user_access_level
        
        params = request.GET.copy()
        user_access_level = get_user_access_level(request.user)
        
        # Full access users default to map view, others default to list view
        if user_access_level == 'full':
            return redirect(f'/search-map/?{urlencode(params)}')
        else:
            return redirect(f'/search/?{urlencode(params)}')
    
    # Otherwise, show the homepage
    return render(request, 'checker/search.html', {
        'user': request.user,
        'query': '',
        'per_page': 25,
        'sort_by': 'relevance',
        'sort_order': 'desc',
        'status_filter': 'all',
        'auction_filter': '',
        'technology_filter': '',
        'expanded_postcodes': [],  # Fix template variable
    })

@access_required
def search_components_optimized(request):
    """
    EGRESS-OPTIMIZED search view using LocationGroup instead of Component
    Provides 90%+ egress reduction compared to old Component-based search
    """
    start_time = time.time()
    
    # MONITORING: Count database queries
    from django.db import connection
    queries_before = len(connection.queries)
    
    # Get search parameters - support both 'q' and 'query'
    query = request.GET.get('query', request.GET.get('q', '')).strip()
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    technology_filter = request.GET.get('technology', '')
    company_filter = request.GET.get('company', '')
    
    # Initialize timing
    timings = {}
    
    # Search for companies directly in the database (FAST SQL-based search)
    company_start = time.time()
    company_links = []
    if query:
        try:
            # Use raw SQL to search company names in LocationGroup's JSON field
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
                # Use normalized company name for URL (to match URL routing)
                normalized_company_name = normalize(company['company_name'])
                company_links.append({
                    'html': f'''
                        <div>
                            <strong><a href="/company-list/{normalized_company_name}/">{company['company_name']}</a></strong>
                            <div class="mt-1 mb-1"><span class="text-muted">{company['component_count']} components</span></div>
                        </div>
                    '''
                })
            
            logger.info(f"Database company search found {len(companies)} matches in {time.time() - company_start:.3f}s")
            
        except Exception as e:
            logger.error(f"Company search error: {e}")
            company_links = []
    
    timings['company_search'] = time.time() - company_start
    
    # Use LocationGroup search (EGRESS OPTIMIZED)
    location_search_start = time.time()
    
    if query:
        logger.info(f"=== OPTIMIZED SEARCH: Processing query '{query}' ===")
        # Check if it's likely a postcode search
        query_upper = query.upper()
        is_postcode_search = (
            len(query_upper) <= 4 and 
            query_upper[:2].isalpha() and 
            any(c.isdigit() for c in query_upper)
        )
        
        if is_postcode_search:
            # Direct postcode search
            location_groups = LocationGroup.objects.filter(
                Q(outward_code__iexact=query_upper) |
                Q(outward_code__istartswith=query_upper)
            )
        else:
            # Handle multi-word queries
            query_parts = query.split()
            
            if len(query_parts) > 1:
                # Multi-word search: each word must match somewhere
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
                    component_filter &= part_filter
                
                # Find unique locations that have matching components
                matching_locations = Component.objects.filter(
                    component_filter
                ).values_list('location', flat=True).distinct()
                
                # Get LocationGroups for these locations
                location_groups = LocationGroup.objects.filter(location__in=matching_locations)
                
                # For multi-word company searches, also include co-located facilities
                if location_groups.exists():
                    # Get exact postcodes from direct matches
                    direct_match_postcodes = list(location_groups.values_list('outward_code', flat=True).distinct())
                    
                    if direct_match_postcodes and len(direct_match_postcodes) <= 5:  # Limit to 5 postcodes for egress control
                        logger.info(f"Adding co-located facilities for multi-word search '{query}' at postcodes: {direct_match_postcodes}")
                        
                        # Find other locations at these exact postcodes
                        colocated_filter = Q()
                        for postcode in direct_match_postcodes:
                            colocated_filter |= Q(outward_code=postcode)
                        
                        colocated_groups = LocationGroup.objects.filter(colocated_filter)
                        location_groups = location_groups | colocated_groups
                        location_groups = location_groups.distinct()
            else:
                # Single word search
                location_groups = LocationGroup.objects.filter(
                    Q(location__icontains=query) |
                    Q(county__icontains=query) |
                    Q(companies__icontains=query) |
                    Q(technologies__icontains=query) |
                    Q(descriptions__icontains=query) |
                    Q(cmu_ids__icontains=query)
                )
                
                # Only do postcode expansion for place name searches, not company name searches
                # Check if this looks like a company/technology search by checking if the query
                # appears as a company name or technology in the database
                is_company_search = LocationGroup.objects.filter(
                    companies__icontains=f'"{query}"'  # Look for exact company name matches
                ).exists() or LocationGroup.objects.filter(
                    technologies__icontains=f'"{query}"'  # Look for exact technology matches  
                ).exists()
                
                # Also check if query is likely a company name by checking if it appears
                # in company fields but mainly in location descriptions (like Honda)
                company_mentions = LocationGroup.objects.filter(
                    Q(companies__icontains=query) | Q(descriptions__icontains=query)
                ).count()
                
                pure_location_matches = LocationGroup.objects.filter(
                    Q(county__iexact=query)  # Exact county matches
                ).count()
                
                # If we have location description mentions but no pure location matches,
                # and the term doesn't appear in many places, it's likely a company search
                if not is_company_search and company_mentions > 0 and pure_location_matches == 0:
                    # Check if this query commonly appears in location descriptions (company facility)
                    location_description_matches = LocationGroup.objects.filter(
                        location__icontains=query
                    ).exclude(
                        Q(county__icontains=query)
                    ).count()
                    
                    if location_description_matches > 0 and location_description_matches <= 5:
                        is_company_search = True
                        logger.info(f"'{query}' appears to be a company name (found in {location_description_matches} location descriptions)")
                
                # Only do postcode expansion if this is NOT a company search
                if not is_company_search:
                    area_postcodes = get_all_postcodes_for_area(query)
                    if area_postcodes:
                        logger.info(f"Place name search for '{query}' found {len(area_postcodes)} postcodes")
                        postcode_filter = Q()
                        for postcode in area_postcodes:
                            postcode_filter |= Q(outward_code=postcode)
                        
                        area_groups = LocationGroup.objects.filter(postcode_filter)
                        location_groups = location_groups | area_groups
                        location_groups = location_groups.distinct()
                else:
                    logger.info(f"Skipping postcode expansion for '{query}' - detected as company/technology search")
                    
                    # For company searches, include other facilities at the exact same postcodes
                    # This finds co-located facilities with minimal egress impact
                    if location_groups.exists():
                        # Get exact postcodes from direct matches
                        direct_match_postcodes = list(location_groups.values_list('outward_code', flat=True).distinct())
                        
                        if direct_match_postcodes and len(direct_match_postcodes) <= 5:  # Limit to 5 postcodes for egress control
                            logger.info(f"Adding co-located facilities for '{query}' at postcodes: {direct_match_postcodes}")
                            
                            # Find other locations at these exact postcodes
                            colocated_filter = Q()
                            for postcode in direct_match_postcodes:
                                colocated_filter |= Q(outward_code=postcode)
                            
                            colocated_groups = LocationGroup.objects.filter(colocated_filter)
                            location_groups = location_groups | colocated_groups
                            location_groups = location_groups.distinct()
    else:
        # No query - get all LocationGroups
        location_groups = LocationGroup.objects.all()
    
    # OPTIMIZED: Apply status filter at database level
    if status_filter == 'active':
        # Use pre-calculated is_active field for maximum performance
        location_groups = location_groups.filter(is_active=True)
    elif status_filter == 'inactive':
        # Use pre-calculated is_active field for maximum performance
        location_groups = location_groups.filter(is_active=False)
    
    # OPTIMIZED: Apply auction year filter at database level
    if auction_filter:
        location_groups = location_groups.filter(
            auction_years__icontains=auction_filter
        )
    
    # Apply technology filter
    if technology_filter and technology_filter != 'all':
        location_groups = location_groups.filter(technologies__has_key=technology_filter)
    
    # Apply company filter
    if company_filter and company_filter != 'all':
        location_groups = location_groups.filter(companies__has_key=company_filter)
    
    # Apply sorting
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'mw':
        order_field = 'normalized_capacity_mw'
    elif sort_by == 'components':
        order_field = 'component_count'
    elif sort_by == 'date':
        order_field = 'location'  # Fallback for now
    else:
        order_field = 'location'
    
    # Apply sort order - desc means reverse order
    if sort_order == 'desc':
        order_field = f'-{order_field}'
    
    location_groups = location_groups.order_by(order_field)
    
    timings['location_search'] = time.time() - location_search_start
    
    # OPTIMIZED: Calculate totals using database aggregation BEFORE pagination
    count_start = time.time()
    totals = location_groups.aggregate(
        total_locations=Count('id'),
        total_components=Sum('component_count')
    )
    timings['component_count'] = time.time() - count_start
    
    # EXPERIMENTAL: Test O3's cached filter approach vs current result-based filtering  
    # Default to result-based filters for better UX (only show relevant options), allow override for testing
    use_cached_filters = request.GET.get('use_cached_filters', 'false') == 'true'
    
    if use_cached_filters:
        # O3 APPROACH: Pre-computed cached filters (complete data, no row fetching)
        logger.info("🚀 Using O3 cached filter approach")
        filter_start = time.time()
        
        cached_options = get_complete_filter_options()
        auction_years = cached_options['auction_years']
        technologies = cached_options['technologies']
        companies = cached_options['companies']
        
        timings['cached_filters'] = time.time() - filter_start
        logger.info(f"✅ Cached filters: {len(technologies)} techs, {len(companies)} companies, {len(auction_years)} years in {timings['cached_filters']:.3f}s")
    else:
        # CURRENT APPROACH: Result-based filters (complete but inefficient, fetches all IDs)
        logger.info("📊 Using current result-based approach")
        filter_start = time.time()
        
        # Get filter options from CURRENT SEARCH RESULTS using sampling (like map view)
        # This shows only relevant options based on the current query/filters
        logger.info("Fetching filter options from current search results...")
        
        # OPTIMIZATION: Use sampling approach to avoid massive egress on large result sets
        total_locations = location_groups.count()
        if total_locations <= 500:
            # For smaller datasets, use all locations for complete dropdown data
            sample_size = total_locations
            result_ids = list(location_groups.values_list('id', flat=True))
        else:
            # For larger datasets, use sampling to keep egress low
            sample_size = 500
            result_ids = list(location_groups.values_list('id', flat=True)[:sample_size])
            logger.info(f"📊 Using sample of {sample_size} locations from {total_locations} total results for filter building")
        
        if result_ids:
            # Use raw SQL for efficiency to get unique values from current results only
            with connection.cursor() as cursor:
                # Get auction years from current results only
                cursor.execute("""
                    SELECT DISTINCT jsonb_array_elements_text(auction_years::jsonb)
                    FROM checker_locationgroup 
                    WHERE id = ANY(%s) AND auction_years IS NOT NULL
                    ORDER BY 1 DESC
                """, [result_ids])
                auction_years = [row[0] for row in cursor.fetchall()]
                
                # Get technologies from current results only
                cursor.execute("""
                    SELECT DISTINCT jsonb_object_keys(technologies::jsonb)
                    FROM checker_locationgroup 
                    WHERE id = ANY(%s) AND technologies IS NOT NULL
                    ORDER BY 1
                """, [result_ids])
                technologies = [row[0] for row in cursor.fetchall()]
                
                # Get companies from current results only
                cursor.execute("""
                    SELECT DISTINCT jsonb_object_keys(companies::jsonb)
                    FROM checker_locationgroup 
                    WHERE id = ANY(%s) AND companies IS NOT NULL
                    ORDER BY 1
                """, [result_ids])
                companies = [row[0] for row in cursor.fetchall()]
        else:
            # No results, so no filter options
            auction_years = []
            technologies = []
            companies = []
        
        timings['filter_options'] = time.time() - filter_start
        logger.info(f"📊 Result-based filters: {len(technologies)} techs, {len(companies)} companies from {len(result_ids)} IDs in {timings['filter_options']:.3f}s")
    
    # OPTIMIZED: Select only needed fields for pagination
    optimized_locations = location_groups.only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    # Paginate BEFORE processing (key optimization!)
    pagination_start = time.time()
    paginator = Paginator(optimized_locations, per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    timings['pagination'] = time.time() - pagination_start
    
    load_time = time.time() - start_time
    
    # MONITORING: Calculate optimization metrics
    queries_after = len(connection.queries)
    query_count = queries_after - queries_before
    
    # Calculate rows fetched based on actual approach used
    if use_cached_filters:
        # Cached approach: only page results + minimal filter metadata
        rows_fetched = len(page_obj)  # Only actual search results fetched from DB
        filter_metadata_bytes = (len(auction_years) + len(technologies) + len(companies)) * 20  # Cached filter names
        page_data_bytes = len(page_obj) * 10 * 50  # Page data: 10 fields * 50 bytes
        estimated_bytes = page_data_bytes + filter_metadata_bytes
    else:
        # Result-based approach: page results + sampled IDs for filter building
        sample_size = min(500, totals['total_locations']) if totals['total_locations'] > 500 else totals['total_locations']
        rows_fetched = len(page_obj) + sample_size  # Page + sample IDs fetched
        estimated_bytes = rows_fetched * 10 * 50  # 10 fields * ~50 bytes per field
    
    # Enhanced logging with optimization metrics
    approach_label = "CACHED" if use_cached_filters else "RESULT-BASED"
    logger.info(f"🔍 {approach_label} search for '{query}':")
    logger.info(f"   📊 Total locations: {totals['total_locations']}")
    logger.info(f"   📋 Displayed: {len(page_obj)} items (page {page})")
    logger.info(f"   🔍 Filter options: {len(auction_years)} years, {len(technologies)} techs, {len(companies)} companies")
    logger.info(f"   💾 Database queries: {query_count}")
    logger.info(f"   📦 Rows fetched: {rows_fetched}")
    logger.info(f"   📊 Estimated data: {estimated_bytes:,} bytes ({estimated_bytes/1024:.1f} KB)")
    if use_cached_filters:
        logger.info(f"   🎯 Breakdown: {page_data_bytes:,} bytes (page data) + {filter_metadata_bytes:,} bytes (filter names)")
    logger.info(f"   ⏱️  Load time: {load_time:.3f}s")
    logger.info(f"   🔧 Filters: status={status_filter}, auction={auction_filter}, tech={technology_filter}")
    
    # Compare to old approach estimate
    if totals['total_locations']:
        old_estimate = totals['total_locations'] * 24 * 50  # All fields, all locations
        reduction = ((old_estimate - estimated_bytes) / old_estimate) * 100
        logger.info(f"   💡 Estimated egress reduction: {reduction:.1f}% ({old_estimate:,} → {estimated_bytes:,} bytes)")
    
    # Build context
    context = {
        'query': query,
        'page_obj': page_obj,
        'company_links': company_links,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'total_components': totals['total_components'] or 0,
        'total_locations': totals['total_locations'] or 0,
        'locations_on_page': len(page_obj),
        'api_time': load_time,
        'timings': timings,
        'page': page,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'auction_years': auction_years,
        'technology_filter': technology_filter,
        'technologies': technologies,
        'company_filter': company_filter,
        'companies': companies,
        'user': request.user,
        'expanded_postcodes': [],  # Fix template variable
    }
    
    return render(request, 'checker/search_locationgroup_optimized.html', context)