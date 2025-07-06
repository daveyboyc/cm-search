"""
Simple search map view that calls the existing search API
"""
from django.shortcuts import render
from django.conf import settings
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Q, Sum, Count
from django.db import connection
from django.views.decorators.cache import cache_page
import logging
import time as time_module
import hashlib
import json

from .models import LocationGroup, Component
from .services.location_search_static import get_locations_for_postcode
from .services.filter_options import get_complete_filter_options
from .services.company_index_postgresql import get_company_links_html_postgresql
from .decorators.access_required import map_access_required
from .decorators.bot_protection import bot_protected_view

logger = logging.getLogger(__name__)

@bot_protected_view(rate='5/m')  # Strict rate limiting for bots
# Removed @cache_page - using comprehensive search result caching instead
def search_map_view_simple(request):
    """Search map view that displays results with a map using optimized search performance"""
    start_time = time_module.time()
    
    # Get search parameters early for cache key generation
    query = request.GET.get('query', request.GET.get('q', '')).strip()
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'asc' if sort_by == 'location' else 'desc')
    status_filter = request.GET.get('status', 'all')
    auction_filter = request.GET.get('auction', '')
    technology_filter = request.GET.get('technology', '')
    company_filter = request.GET.get('company', '')
    
    # Note: Using existing ID-level caching and improved search performance instead of complex result caching
    
    # COMPREHENSIVE PERFORMANCE MONITORING
    performance_log = {
        'start_time': start_time,
        'query': request.GET.get('query', request.GET.get('q', '')).strip(),
        'timings': {},
        'db_queries': {},
        'bottlenecks': []
    }
    
    # MONITORING: Count database queries
    from django.db import connection
    queries_before = len(connection.queries)
    performance_log['db_queries']['initial'] = queries_before
    
    # Additional parameters
    is_quick_search = request.GET.get('quick_search', 'false').lower() == 'true'
    
    # Handle explicit sort_order override
    if 'sort_order' in request.GET:
        sort_order = request.GET.get('sort_order')
    
    # Debug logging for sort order issues
    logger.debug(f"🔍 SORT DEBUG: sort_by='{sort_by}', sort_order='{sort_order}', explicit_order={'sort_order' in request.GET}")
    
    # PERFORMANCE OPTIMIZATION: Redirect single-filter queries to optimized dedicated pages
    # These pages use LocationGroup table directly and are much faster than search-map filtering
    if not query and not is_quick_search:  # Only for "All Locations" type queries
        if technology_filter and not company_filter and not auction_filter:
            # Single technology filter - redirect to optimized technology page
            from django.shortcuts import redirect
            from django.urls import reverse
            try:
                tech_url = reverse('technology_detail_map', kwargs={'technology_name': technology_filter})
                # Preserve pagination and sorting
                redirect_params = []
                if page != 1:
                    redirect_params.append(f'page={page}')
                if per_page != 25:
                    redirect_params.append(f'per_page={per_page}')
                if sort_by != 'relevance':
                    redirect_params.append(f'sort_by={sort_by}')
                if sort_order != 'desc':
                    redirect_params.append(f'sort_order={sort_order}')
                if status_filter != 'all':
                    redirect_params.append(f'status={status_filter}')
                
                if redirect_params:
                    tech_url += '?' + '&'.join(redirect_params)
                
                logger.info(f"🚀 REDIRECT: Technology filter '{technology_filter}' -> {tech_url}")
                return redirect(tech_url)
            except:
                # If redirect fails, continue with normal search-map processing
                pass
        
        elif company_filter and not technology_filter and not auction_filter:
            # Single company filter - redirect to optimized company page  
            from django.shortcuts import redirect
            from django.urls import reverse
            try:
                company_url = reverse('company_detail_map', kwargs={'company_name': company_filter})
                # Preserve pagination and sorting
                redirect_params = []
                if page != 1:
                    redirect_params.append(f'page={page}')
                if per_page != 25:
                    redirect_params.append(f'per_page={per_page}')
                if sort_by != 'relevance':
                    redirect_params.append(f'sort_by={sort_by}')
                if sort_order != 'desc':
                    redirect_params.append(f'sort_order={sort_order}')
                if status_filter != 'all':
                    redirect_params.append(f'status={status_filter}')
                
                if redirect_params:
                    company_url += '?' + '&'.join(redirect_params)
                
                logger.info(f"🚀 REDIRECT: Company filter '{company_filter}' -> {company_url}")
                return redirect(company_url)
            except:
                # If redirect fails, continue with normal search-map processing
                pass
    
    # If relevance sorting is requested but there's no query, default to location sorting
    if sort_by == 'relevance' and not query:
        logger.info(f"🔄 Converting relevance to location sort (no query)")
        sort_by = 'location'
        sort_order = 'asc'  # Default to A-Z (ascending) for location sorting
    
    # STATIC PAGE CACHING: Check for cached "All Locations" pages
    # This eliminates database queries for 90% of users who access first 2 pages
    # NOTE: Static cache now supports both A-Z (ascending) and Z-A (descending) sorting
    cached_response = None
    if not query and sort_by == 'location':  # All locations - both A-Z and Z-A
        from .services.static_page_cache import static_cache
        
        cached_data = static_cache.get_cached_page(
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            auction_filter=auction_filter,
            technology_filter=technology_filter,
            company_filter=company_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        if cached_data:
            # Return cached response immediately - no database queries needed!
            logger.info(f"🚀 CACHE HIT: Serving page {page} from cache - 0 database queries")
            context = cached_data['page_data']
            context['from_cache'] = True
            context['cache_timestamp'] = cached_data['cache_meta']['created_at']
            
            response = render(request, 'checker/search_with_map_combined.html', context)
            
            # Add HTTP caching headers for cached responses
            from django.utils.http import http_date
            from django.utils.cache import patch_cache_control
            import time
            
            # Set cache headers for 1 hour (cached content is fresh)
            patch_cache_control(response, max_age=3600, public=True)
            
            # Add ETag based on cache checksum
            etag = f'"{cached_data["cache_meta"]["checksum"]}-{page}"'
            response['ETag'] = etag
            
            # Add Last-Modified header
            response['Last-Modified'] = http_date(time_module.time())
            
            return response
    
    # Initialize timing
    timings = {}
    
    # REDIS-CACHED COMPANY SEARCH - Target: 130ms → 5ms (96% improvement)
    # MEMORY SAFE: Only cache common searches to prevent Redis overflow
    company_start = time_module.time()
    company_links = []
    if query and len(query) >= 4 and query.lower() not in ['battery', 'solar', 'wind', 'gas', 'diesel']:  # Skip for very broad technology terms
        try:
            # USE PRE-BUILT COMPANY INDEX from PostgreSQL (fast search ~5ms)
            # This replaces the Redis cache with PostgreSQL table and indexed search
            # The table contains all 1,685 companies with pre-rendered HTML
            html_links, match_count, search_time = get_company_links_html_postgresql(query)
            
            if html_links:
                # Convert HTML strings to the expected format
                company_links = []
                for html in html_links[:10]:  # Limit to 10 results
                    company_links.append({'html': html})
                
                logger.info(f"🚀 Company index search for '{query}' - found {match_count} matches in {search_time:.3f}s")
                performance_log['timings']['company_index_search'] = search_time
            else:
                logger.info(f"⚡ Company index search for '{query}' - no matches found in {search_time:.3f}s")
                performance_log['timings']['company_index_search'] = search_time
                company_links = []
            
        except Exception as e:
            logger.error(f"Company search error: {e}")
            company_links = []
    
    performance_log['timings']['company_search'] = time_module.time() - company_start
    
    # Use LocationGroup search
    location_search_start = time_module.time()
    performance_log['db_queries']['before_search'] = len(connection.queries)
    
    if query:
        logger.info(f"=== SEARCH MAP VIEW: Processing query '{query}' ===")
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
            
            # If postcode search returns few results, also search location names
            # This handles cases like "SW16" which could be in location names
            if location_groups.count() < 3:
                location_name_groups = LocationGroup.objects.filter(
                    Q(location__icontains=query) |
                    Q(county__icontains=query)
                )
                location_groups = location_groups | location_name_groups
                location_groups = location_groups.distinct()
        else:
            # Handle multi-word queries
            query_parts = query.split()
            
            if len(query_parts) > 1:
                # Multi-word search: use OR logic for quick searches, AND for regular searches
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
                    if is_quick_search:
                        # Quick search: use OR logic (any term matches)
                        component_filter |= part_filter
                    else:
                        # Regular search: use AND logic (all terms must match)
                        component_filter &= part_filter
                
                # FAST: Search LocationGroup directly instead of scanning Component table
                location_filter = Q()
                for part in query_parts:
                    part_filter = (
                        Q(location__icontains=part) |
                        Q(companies__icontains=part) |
                        Q(descriptions__icontains=part) |
                        Q(cmu_ids__icontains=part) |
                        Q(technologies__icontains=part) |
                        Q(county__icontains=part)
                    )
                    if is_quick_search:
                        location_filter |= part_filter
                    else:
                        location_filter &= part_filter
                
                location_groups = LocationGroup.objects.filter(location_filter)
            else:
                # Single word search - check cache first for common searches
                cache_key = f"location_search:{query.lower()}:{status_filter}:{auction_filter}:{technology_filter}:{company_filter}"
                cached_ids = cache.get(cache_key)
                
                if cached_ids is not None:
                    # Use cached results
                    logger.info(f"Cache HIT for search '{query}' - using {len(cached_ids)} cached location IDs")
                    direct_matches = LocationGroup.objects.filter(id__in=cached_ids)
                else:
                    # Perform ultra-fast search using PostgreSQL full-text search
                    from django.contrib.postgres.search import SearchQuery, SearchRank
                    
                    # Create search query - handles multiple words, phrases, and boolean logic
                    search_query = SearchQuery(query, config='english')
                    
                    # Use full-text search with ranking for relevance
                    direct_matches = LocationGroup.objects.filter(
                        search_vector=search_query
                    ).annotate(
                        search_rank=SearchRank('search_vector', search_query)
                    ).order_by('-search_rank')
                    
                    logger.info(f"Full-text search for '{query}' using SearchVector (ultra-fast PostgreSQL search)")
                    
                    # Cache the IDs for 5 minutes for single-word searches
                    if len(query.split()) == 1 and len(query) >= 3:
                        ids_to_cache = list(direct_matches.values_list('id', flat=True)[:500])  # Limit to 500 IDs
                        cache.set(cache_key, ids_to_cache, timeout=300)  # 5 minutes
                        logger.info(f"Cached {len(ids_to_cache)} location IDs for search '{query}'")
                
                # Check if it's a postcode-based search - use smart logic to determine when to run postcode expansion
                # SMART: Always run for geographic queries (cities, postcodes), skip for business/tech queries
                area_start = time_module.time()
                
                # Skip postcode expansion for obvious business/technology queries
                if query.lower() in ['boots', 'asda', 'tesco', 'sainsbury', 'vital', 'battery', 'solar', 'wind', 'gas', 'storage', 'hydro', 'nuclear', 'biomass', 'coal']:
                    area_locations = []
                    performance_log['timings']['area_postcode_skip'] = time_module.time() - area_start
                    logger.info(f"⚡ Skipped area postcode lookup for common business/tech query: {query}")
                else:
                    # Use FAST static lookup for potential geographic queries
                    area_locations = get_locations_for_postcode(query)
                    performance_log['timings']['area_postcode_lookup'] = time_module.time() - area_start
                
                # INTELLIGENT: Run postcode expansion if we found geographic matches, regardless of full-text search results
                # This ensures searches like "london", "manchester", "SW11" work properly
                if area_locations:
                    logger.info(f"✅ GEOGRAPHIC search for '{query}' found {len(area_locations)} locations via postcode expansion")
                    # Create filter for the exact locations found
                    location_filter = Q()
                    for location in area_locations:
                        location_filter |= Q(location=location)
                    
                    area_groups = LocationGroup.objects.filter(location_filter)
                    
                    # Combine with full-text search results for maximum coverage
                    if direct_matches.exists():
                        location_groups = direct_matches | area_groups
                        location_groups = location_groups.distinct()
                        logger.info(f"✅ Combined {direct_matches.count()} full-text matches with {area_groups.count()} geographic matches")
                    else:
                        location_groups = area_groups
                        logger.info(f"✅ Using {area_groups.count()} geographic matches (no full-text matches)")
                else:
                    location_groups = direct_matches
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
    
    # Apply sorting with relevance prioritization for text searches
    if sort_by == 'relevance' and query:
        # For text searches, implement relevance-based ordering
        from django.db.models import Case, When, Value, IntegerField
        
        # Prioritize by relevance: company name > description > location > postcode area
        location_groups = location_groups.annotate(
            relevance_score=Case(
                When(companies__icontains=query, then=Value(4)),
                When(descriptions__icontains=query, then=Value(3)),
                When(location__icontains=query, then=Value(2)),
                default=Value(1),  # Postcode matches get lowest priority
                output_field=IntegerField()
            )
        ).order_by('-relevance_score', 'location')
    elif sort_by == 'location':
        order_field = 'location'
        if sort_order == 'desc':
            order_field = f'-{order_field}'
        location_groups = location_groups.order_by(order_field)
    elif sort_by == 'mw':
        order_field = 'normalized_capacity_mw'
        if sort_order == 'desc':
            order_field = f'-{order_field}'
        location_groups = location_groups.order_by(order_field)
    elif sort_by == 'components':
        order_field = 'component_count'
        if sort_order == 'desc':
            order_field = f'-{order_field}'
        location_groups = location_groups.order_by(order_field)
    elif sort_by == 'date':
        order_field = 'location'  # Fallback for now
        if sort_order == 'desc':
            order_field = f'-{order_field}'
        location_groups = location_groups.order_by(order_field)
    else:
        # Default relevance ordering for any search
        if query:
            from django.db.models import Case, When, Value, IntegerField
            location_groups = location_groups.annotate(
                relevance_score=Case(
                    When(companies__icontains=query, then=Value(4)),
                    When(descriptions__icontains=query, then=Value(3)),
                    When(location__icontains=query, then=Value(2)),
                    default=Value(1),
                    output_field=IntegerField()
                )
            ).order_by('-relevance_score', 'location')
        else:
            location_groups = location_groups.order_by('location')
    
    performance_log['timings']['location_search'] = time_module.time() - location_search_start
    performance_log['db_queries']['after_search'] = len(connection.queries)
    
    # Filters and sorting completed
    filter_end = time_module.time()
    performance_log['timings']['filters_and_sorting'] = filter_end - location_search_start
    
    # OPTIMIZED: Calculate totals using fast raw SQL BEFORE pagination
    count_start = time_module.time()
    
    # Build the WHERE clause based on applied filters
    where_conditions = []
    params = []
    
    if query:
        if len(query.split()) > 1:
            # Multi-word search
            query_parts = query.split()
            if is_quick_search:
                # OR logic for quick search
                or_conditions = []
                for part in query_parts:
                    or_conditions.append("(location ILIKE %s OR county ILIKE %s OR companies::text ILIKE %s OR technologies::text ILIKE %s OR descriptions::text ILIKE %s OR cmu_ids::text ILIKE %s)")
                    params.extend([f'%{part}%'] * 6)
                where_conditions.append(f"({' OR '.join(or_conditions)})")
            else:
                # AND logic for regular search
                for part in query_parts:
                    where_conditions.append("(location ILIKE %s OR county ILIKE %s OR companies::text ILIKE %s OR technologies::text ILIKE %s OR descriptions::text ILIKE %s OR cmu_ids::text ILIKE %s)")
                    params.extend([f'%{part}%'] * 6)
        else:
            # Single word search
            is_postcode_search = (
                len(query.upper()) <= 4 and 
                query.upper()[:2].isalpha() and 
                any(c.isdigit() for c in query.upper())
            )
            
            if is_postcode_search:
                where_conditions.append("(outward_code ILIKE %s OR outward_code ILIKE %s OR location ILIKE %s OR county ILIKE %s)")
                params.extend([query.upper(), f'{query.upper()}%', f'%{query}%', f'%{query}%'])
            else:
                # PERFORMANCE: Skip expensive area search for common queries
                if query.lower() in ['boots', 'asda', 'tesco', 'sainsbury', 'vital', 'battery', 'solar', 'wind', 'gas']:
                    area_locations = []
                else:
                    # Use FAST static lookup instead of slow API calls
                    area_locations = get_locations_for_postcode(query)
                # FAST: Use static locations directly instead of postcode logic
                if area_locations:
                    # Include direct location matches from static lookup
                    location_conditions = " OR ".join(["location = %s"] * len(area_locations))
                    where_conditions.append(f"(location ILIKE %s OR county ILIKE %s OR companies::text ILIKE %s OR technologies::text ILIKE %s OR descriptions::text ILIKE %s OR cmu_ids::text ILIKE %s OR ({location_conditions}))")
                    params.extend([f'%{query}%'] * 6)
                    params.extend(area_locations)
                else:
                    where_conditions.append("(location ILIKE %s OR county ILIKE %s OR companies::text ILIKE %s OR technologies::text ILIKE %s OR descriptions::text ILIKE %s OR cmu_ids::text ILIKE %s)")
                    params.extend([f'%{query}%'] * 6)
    
    # Add status filter
    if status_filter == 'active':
        where_conditions.append("is_active = %s")
        params.append(True)
    elif status_filter == 'inactive':
        where_conditions.append("is_active = %s")
        params.append(False)
    
    # Add auction filter
    if auction_filter:
        where_conditions.append("auction_years::text ILIKE %s")
        params.append(f'%{auction_filter}%')
    
    # Add technology filter
    if technology_filter and technology_filter != 'all':
        where_conditions.append("technologies ? %s")
        params.append(technology_filter)
    
    # Add company filter
    if company_filter and company_filter != 'all':
        where_conditions.append("companies ? %s")
        params.append(company_filter)
    
    # REDIS-CACHED COUNT QUERIES - Target: 200ms → 2ms (99% improvement)
    # MEMORY SAFE: Only cache common search patterns to prevent Redis overflow
    
    # Create cache key based on query and all filters
    count_cache_key_data = {
        'query': query or '',
        'status': status_filter,
        'auction': auction_filter,
        'technology': technology_filter,
        'company': company_filter,
        'quick_search': is_quick_search
    }
    count_cache_key = f"search_count:{hashlib.md5(json.dumps(count_cache_key_data, sort_keys=True).encode()).hexdigest()[:12]}"
    
    # MEMORY PROTECTION: Only cache count queries for common patterns
    count_should_cache = (
        not query or  # Always cache "All Locations" queries
        len(query) <= 15 or  # Cache short queries (likely common)
        query.lower() in ['asda', 'boots', 'tesco', 'sainsbury', 'morrisons', 'vital', 'battery', 'solar', 'wind', 'gas'] or  # Common searches
        (technology_filter and not query) or  # Technology filter pages
        (company_filter and not query)  # Company filter pages
    )
    
    cached_totals = None
    if count_should_cache:
        cached_totals = cache.get(count_cache_key)
    
    if cached_totals is not None:
        # CACHE HIT: Use cached count results (2ms vs 200ms)
        totals = cached_totals
        logger.info(f"🚀 Count query CACHE HIT for '{query}' - using cached totals: {totals['total_locations']} locations")
        performance_log['timings']['count_cache_hit'] = time_module.time() - count_start
    else:
        # CACHE MISS: Perform database query and cache results
        base_sql = "SELECT COUNT(*) as total_locations, COALESCE(SUM(component_count), 0) as total_components FROM checker_locationgroup"
        if where_conditions:
            base_sql += " WHERE " + " AND ".join(where_conditions)
        
        with connection.cursor() as cursor:
            cursor.execute(base_sql, params)
            result = cursor.fetchone()
            totals = {
                'total_locations': result[0],
                'total_components': result[1]
            }
        
        # MEMORY SAFE CACHING: Only cache common search patterns
        if count_should_cache:
            # Dynamic TTL based on query type
            if not query:  # "All Locations" queries - cache longer
                ttl = 3600  # 1 hour
            elif query.lower() in ['asda', 'boots', 'tesco', 'sainsbury', 'morrisons']:  # Very common
                ttl = 1800  # 30 minutes  
            else:  # Other cacheable queries
                ttl = 900   # 15 minutes
            
            cache.set(count_cache_key, totals, timeout=ttl)
            logger.info(f"💾 Count query CACHED for '{query}' - totals cached for {ttl//60}min")
        else:
            logger.info(f"⚡ Count query NOT CACHED for '{query}' - likely unique query pattern")
        
        performance_log['timings']['count_cache_miss'] = time_module.time() - count_start
    
    performance_log['timings']['component_count'] = time_module.time() - count_start
    
    # PERFORMANCE: Use lazy loading for filters - load via AJAX on dropdown interaction
    # This eliminates filter calculation from main search, making searches instant
    filter_start = time_module.time()
    
    # Show dropdowns with placeholder content - populated by AJAX when clicked
    # For "all locations" (no search query), load all filters directly for better UX
    # Also include when just sorting (empty query or whitespace only)
    # MEMORY FIX: Disable filter loading when query is present to prevent Redis memory spikes
    if not query or query.strip() == '':
        # Load all available filters directly for "all locations" and sorting
        logger.info("🚀 Loading all filters directly for 'all locations' page")
        
        try:
            with connection.cursor() as cursor:
                # Determine order for dropdowns based on main sort
                if sort_by == 'components':
                    # Sort by number of locations (count)
                    tech_order = "ORDER BY location_count DESC, tech"
                    company_order = "ORDER BY location_count DESC, company"
                elif sort_by == 'mw':
                    # Sort by total capacity
                    tech_order = "ORDER BY total_capacity DESC NULLS LAST, tech"
                    company_order = "ORDER BY total_capacity DESC NULLS LAST, company"
                else:
                    # Default alphabetical sort
                    tech_order = "ORDER BY tech"
                    company_order = "ORDER BY company"
                
                # Build WHERE clauses based on current filters
                tech_where_clauses = ["technologies IS NOT NULL"]
                company_where_clauses = ["companies IS NOT NULL"]
                
                # Filter technologies by selected company
                if company_filter:
                    tech_where_clauses.append(f"companies ? '{company_filter}'")
                
                # Filter companies by selected technology  
                if technology_filter:
                    company_where_clauses.append(f"technologies ? '{technology_filter}'")
                
                # Filter by status if specified
                if status_filter == 'active':
                    tech_where_clauses.append("auction_years::text ~ '202[4-9]'")
                    company_where_clauses.append("auction_years::text ~ '202[4-9]'")
                elif status_filter == 'inactive':
                    tech_where_clauses.append("NOT (auction_years::text ~ '202[4-9]')")
                    company_where_clauses.append("NOT (auction_years::text ~ '202[4-9]')")
                
                # Filter by auction year if specified
                if auction_filter:
                    tech_where_clauses.append(f"auction_years::text ILIKE '%{auction_filter}%'")
                    company_where_clauses.append(f"auction_years::text ILIKE '%{auction_filter}%'")
                
                tech_where = " AND ".join(tech_where_clauses)
                company_where = " AND ".join(company_where_clauses)
                
                # Get unique technologies with enhanced sorting
                if sort_by in ['components', 'mw']:
                    cursor.execute(f"""
                        SELECT tech, COUNT(*) as location_count, 
                               COALESCE(SUM(normalized_capacity_mw), 0) as total_capacity
                        FROM (
                            SELECT jsonb_object_keys(technologies) as tech, normalized_capacity_mw
                            FROM checker_locationgroup 
                            WHERE {tech_where}
                        ) tech_data
                        GROUP BY tech
                        {tech_order}
                        LIMIT 300
                    """)
                    technologies = [row[0] for row in cursor.fetchall()]
                else:
                    cursor.execute(f"""
                        SELECT DISTINCT jsonb_object_keys(technologies) as tech
                        FROM checker_locationgroup 
                        WHERE {tech_where}
                        ORDER BY tech
                        LIMIT 300
                    """)
                    technologies = [row[0] for row in cursor.fetchall()]
                
                # Get unique companies with enhanced sorting  
                if sort_by in ['components', 'mw']:
                    cursor.execute(f"""
                        SELECT company, COUNT(*) as location_count,
                               COALESCE(SUM(normalized_capacity_mw), 0) as total_capacity
                        FROM (
                            SELECT jsonb_object_keys(companies) as company, normalized_capacity_mw
                            FROM checker_locationgroup 
                            WHERE {company_where}
                        ) company_data
                        GROUP BY company
                        {company_order}
                        LIMIT 2000
                    """)
                    companies = [row[0] for row in cursor.fetchall()]
                else:
                    cursor.execute(f"""
                        SELECT DISTINCT jsonb_object_keys(companies) as company
                        FROM checker_locationgroup 
                        WHERE {company_where}
                        ORDER BY company
                        LIMIT 2000
                    """)
                    companies = [row[0] for row in cursor.fetchall()]
                
                # Get all unique auction years directly
                cursor.execute("""
                    SELECT DISTINCT jsonb_array_elements_text(auction_years) as year
                    FROM checker_locationgroup 
                    WHERE auction_years IS NOT NULL
                    ORDER BY year DESC
                    LIMIT 50
                """)
                auction_years = [row[0] for row in cursor.fetchall()]
                
                logger.info(f"✅ Loaded {len(technologies)} technologies, {len(companies)} companies, {len(auction_years)} years for all locations")
                
        except Exception as e:
            logger.error(f"Error loading all filters: {e}")
            # Fallback to lazy loading
            auction_years = ['Loading...']
            technologies = ['Loading...'] 
            companies = ['Loading...']
    else:
        # For searches, use lazy loading to prevent Redis memory spikes
        logger.info("💾 MEMORY FIX: Using lazy loading for searches to prevent Redis memory spikes")
        auction_years = ['Loading...']
        technologies = ['Loading...'] 
        companies = ['Loading...']
    
    performance_log['timings']['lazy_filters'] = time_module.time() - filter_start
    logger.info("🚀 Using lazy loading - filters will load on dropdown interaction")
    
    # OPTIMIZED: Select only needed fields for pagination and prefetch related data
    # Use only() to load exactly what the template needs (like detail views)
    # Also prefetch representative_component to avoid N+1 queries for colocation checks
    optimized_locations = location_groups.select_related(
        'representative_component'
    ).only(
        'id', 'location', 'component_count', 'descriptions', 'technologies', 
        'companies', 'latitude', 'longitude', 'outward_code', 'is_active', 
        'auction_years', 'normalized_capacity_mw',
        'representative_component__id', 'representative_component__full_postcode'
    )
    
    # Paginate BEFORE processing (key optimization!)
    pagination_start = time_module.time()
    paginator = Paginator(optimized_locations, per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    performance_log['timings']['pagination'] = time_module.time() - pagination_start
    performance_log['db_queries']['after_pagination'] = len(connection.queries)
    
    # PERFORMANCE: Prefetch colocation data to avoid N+1 queries in template
    # This prevents 25+ queries when rendering search results with postcode links
    colocation_start = time_module.time()
    
    # Get all postcodes for current page locations
    location_ids = [loc.id for loc in page_obj]
    if location_ids:
        # First, get all postcodes from locations on this page
        page_postcodes = []
        for location in page_obj:
            if location.representative_component and location.representative_component.full_postcode:
                page_postcodes.append(location.representative_component.full_postcode)
        
        # Then count ALL location groups at these postcodes (not just ones on current page)
        from django.db.models import Count
        if page_postcodes:
            postcodes_data = LocationGroup.objects.filter(
                representative_component__full_postcode__in=page_postcodes
            ).values('representative_component__full_postcode').annotate(
                count=Count('id', distinct=True)
            ).filter(count__gt=1)
            
            # Create a dict of postcode -> count for quick lookup
            postcode_counts = {item['representative_component__full_postcode']: item['count'] for item in postcodes_data}
        else:
            postcode_counts = {}
        
        # Attach colocation info to each location
        for location in page_obj:
            if location.representative_component and location.representative_component.full_postcode:
                postcode = location.representative_component.full_postcode
                if postcode in postcode_counts and postcode_counts[postcode] > 1:
                    location.colocation_info_cached = {
                        'postcode': postcode,
                        'count': postcode_counts[postcode]
                    }
                else:
                    location.colocation_info_cached = None
            else:
                location.colocation_info_cached = None
    
    performance_log['timings']['colocation_prefetch'] = time_module.time() - colocation_start
    
    # PERFORMANCE: Disabled expensive related locations feature - not displayed in template
    # This was causing 50+ database queries per page (2 per location) for unused functionality
    # TODO: If needed, implement as single efficient query or async loading
    related_info = {}
    performance_log['timings']['related_locations'] = 0.0
    
    # Check if we should show search suggestions (no results found)
    search_suggestions = []
    did_you_mean = None
    
    if query and totals['total_components'] == 0 and len(company_links) == 0:
        # No results found, get search suggestions
        try:
            from .services.search_suggestions import get_multiple_suggestions
            suggestions = get_multiple_suggestions(query)
            if suggestions:
                search_suggestions = suggestions[:3]  # Limit to 3 suggestions
                did_you_mean = suggestions[0] if suggestions else None
                logger.info(f"Generated search suggestions for '{query}': {suggestions}")
        except Exception as e:
            logger.error(f"Error generating search suggestions for '{query}': {e}")
    
    # Debug final sort values
    logger.debug(f"📋 FINAL SORT VALUES: sort_by='{sort_by}', sort_order='{sort_order}'")
    
    # Build context
    context = {
        'q': query,
        'query': query,  # Template expects 'query' instead of 'q'
        'page_obj': page_obj,
        'company_links': company_links,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'total_components': totals['total_components'] or 0,
        'total_locations': totals['total_locations'] or 0,
        'locations_on_page': len(page_obj),
        'api_time': time_module.time() - start_time,
        'timings': performance_log['timings'],
        'page': page,
        'status_filter': status_filter,
        'auction_filter': auction_filter,
        'auction_years': auction_years,
        'technology_filter': technology_filter,
        'technologies': technologies,
        'company_filter': company_filter,
        'companies': companies,
        'related_info': related_info,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY if hasattr(settings, 'GOOGLE_MAPS_API_KEY') else '',
        'user': request.user,
        'search_suggestions': search_suggestions,
        'did_you_mean': did_you_mean,
    }
    
    # MONITORING: Calculate optimization metrics
    queries_after = len(connection.queries)
    query_count = queries_after - queries_before
    
    # Calculate egress metrics - lazy loading approach
    rows_fetched = len(page_obj)  # Only page data, no filter calculation
    approach_label = "LAZY"
    
    # More realistic egress estimate based on actual field sizes and template overhead
    # Average LocationGroup with only() applied: ~400 bytes per result (like detail views)
    # Template overhead (HTML, CSS, JS): ~20KB base
    data_bytes = rows_fetched * 400  # Optimized per-result size using only()
    template_overhead = 20000  # Base template size
    estimated_bytes = data_bytes + template_overhead
    
    # Enhanced logging with optimization metrics
    logger.info(f"🗺️  {approach_label} search map view for '{query}':")
    logger.info(f"   📊 Total locations: {totals['total_locations']}")
    logger.info(f"   📋 Displayed: {len(page_obj)} items (page {page})")
    logger.info(f"   🚀 Filter source: Lazy loading (AJAX on demand)")
    logger.info(f"   📊 Filter counts: 0 (loaded on dropdown interaction)")
    logger.info(f"   💾 Database queries: {query_count}")
    logger.info(f"   📦 Rows fetched: {rows_fetched}")
    logger.info(f"   📊 Estimated data: {estimated_bytes:,} bytes ({estimated_bytes/1024:.1f} KB)")
    logger.info(f"   ⏱️  Load time: {context['api_time']:.3f}s")
    logger.info(f"   ⚡ Count query time: {performance_log['timings']['component_count']:.3f}s (FAST SQL)")
    logger.info(f"   🔧 Filters: status={status_filter}, auction={auction_filter}, tech={technology_filter}")
    
    # Show massive improvement from SQL optimization
    if performance_log['timings']['component_count'] > 1.0:
        logger.warning(f"   ⚠️  Count query took {performance_log['timings']['component_count']:.3f}s - may need optimization")
    else:
        logger.info(f"   ✅ Count query optimized - was taking 3-5s with Django ORM, now {performance_log['timings']['component_count']:.3f}s with raw SQL")
    
    # Show massive savings from lazy loading
    # Old approach: same results + expensive filter calculation (adds ~25KB of filter data)
    filter_calculation_overhead = 25000  # Filters for all technologies, companies, years
    old_approach_estimate = estimated_bytes + filter_calculation_overhead  
    lazy_savings = filter_calculation_overhead  # The filter overhead we're avoiding
    logger.info(f"   ⚡ Lazy loading saves: {lazy_savings:,} bytes ({lazy_savings/1024:.1f} KB) by deferring filter calculation")
    
    # STATIC PAGE CACHING: Cache eligible pages for future fast access
    # Cache unfiltered location-sorted pages (both A-Z and Z-A)
    if not query and sort_by == 'location':
        from .services.static_page_cache import static_cache
        
        cache_success = static_cache.cache_page(
            page=page,
            page_data=context,
            per_page=per_page,
            status_filter=status_filter,
            auction_filter=auction_filter,
            technology_filter=technology_filter,
            company_filter=company_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        if cache_success:
            logger.info(f"💾 Cached page {page} - next request will be served from cache (0 DB queries)")
    
    # COMPREHENSIVE PERFORMANCE MONITORING - Final Analysis
    total_time = time_module.time() - start_time
    performance_log['total_time'] = total_time
    performance_log['db_queries']['final'] = len(connection.queries)
    performance_log['db_queries']['total'] = performance_log['db_queries']['final'] - performance_log['db_queries']['initial']
    
    # Analyze bottlenecks
    if total_time > 1.5:
        performance_log['bottlenecks'].append(f"Total time {total_time:.3f}s exceeds 1.5s target")
    
    if performance_log['timings'].get('company_search', 0) > 0.5:
        performance_log['bottlenecks'].append(f"Company search: {performance_log['timings']['company_search']:.3f}s")
    
    if performance_log['timings'].get('location_search', 0) > 0.5:
        performance_log['bottlenecks'].append(f"Location search: {performance_log['timings']['location_search']:.3f}s")
    
    if performance_log['timings'].get('pagination', 0) > 0.3:
        performance_log['bottlenecks'].append(f"Pagination: {performance_log['timings']['pagination']:.3f}s")
    
    # Log detailed performance analysis with Redis cache performance
    logger.info(f"🔍 PERFORMANCE ANALYSIS for '{query}':")
    logger.info(f"   ⏱️  Total time: {total_time:.3f}s")
    logger.info(f"   📊 DB queries: {performance_log['db_queries']['total']}")
    
    # Company search performance (using pre-built Redis index)
    if performance_log['timings'].get('company_index_search'):
        logger.info(f"   🚀 Company search: {performance_log['timings']['company_index_search']:.3f}s (POSTGRESQL)")
    elif performance_log['timings'].get('company_cache_hit'):
        logger.info(f"   🚀 Company search: {performance_log['timings']['company_cache_hit']:.3f}s (REDIS CACHE HIT)")
    elif performance_log['timings'].get('company_cache_miss'):
        logger.info(f"   💾 Company search: {performance_log['timings']['company_cache_miss']:.3f}s (REDIS CACHE MISS)")
    else:
        logger.info(f"   🔗 Company search: {performance_log['timings'].get('company_search', 0):.3f}s")
    
    # Count query performance (Redis cached)
    if performance_log['timings'].get('count_cache_hit'):
        logger.info(f"   🚀 Count query: {performance_log['timings']['count_cache_hit']:.3f}s (REDIS CACHE HIT)")
    elif performance_log['timings'].get('count_cache_miss'):
        logger.info(f"   💾 Count query: {performance_log['timings']['count_cache_miss']:.3f}s (REDIS CACHE MISS)")
    else:
        logger.info(f"   📊 Count query: {performance_log['timings'].get('component_count', 0):.3f}s")
    
    logger.info(f"   🏢 Location search: {performance_log['timings'].get('location_search', 0):.3f}s")
    logger.info(f"   📄 Pagination: {performance_log['timings'].get('pagination', 0):.3f}s")
    if performance_log['timings'].get('area_postcode_lookup'):
        logger.info(f"   🗺️  Area postcode lookup: {performance_log['timings']['area_postcode_lookup']:.3f}s")
    if performance_log['timings'].get('area_postcode_skip'):
        logger.info(f"   ⚡ Area postcode SKIPPED: {performance_log['timings']['area_postcode_skip']:.3f}s")
    
    if performance_log['bottlenecks']:
        logger.warning(f"   ⚠️  BOTTLENECKS: {', '.join(performance_log['bottlenecks'])}")
    else:
        logger.info(f"   ✅ No major bottlenecks detected")
    
    # REDIS MEMORY MONITORING: Check memory usage every 10th search
    import random
    if random.randint(1, 10) == 1:  # 10% sampling
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=1)
            memory_info = r.info('memory')
            used_memory_mb = memory_info['used_memory'] / (1024 * 1024)
            max_memory_mb = memory_info.get('maxmemory', 0) / (1024 * 1024) if memory_info.get('maxmemory', 0) > 0 else 64
            memory_percent = (used_memory_mb / max_memory_mb) * 100
            
            if memory_percent > 80:
                logger.warning(f"⚠️  REDIS MEMORY WARNING: {used_memory_mb:.1f}MB/{max_memory_mb:.1f}MB ({memory_percent:.1f}%) - Approaching limit!")
            elif memory_percent > 60:
                logger.info(f"💾 REDIS MEMORY: {used_memory_mb:.1f}MB/{max_memory_mb:.1f}MB ({memory_percent:.1f}%) - Good")
            else:
                logger.debug(f"💾 REDIS MEMORY: {used_memory_mb:.1f}MB/{max_memory_mb:.1f}MB ({memory_percent:.1f}%) - Excellent")
        except Exception as e:
            logger.debug(f"Redis memory check failed: {e}")
    
    response = render(request, 'checker/search_with_map_combined.html', context)
    
    # Full-text search provides significant speed improvement without complex result caching
    
    # Add HTTP caching headers for cacheable responses
    from django.utils.http import http_date
    from django.utils.cache import patch_cache_control
    from .services.static_page_cache import static_cache
    import time
    
    # Determine if this search is cacheable
    is_cacheable = False
    cache_duration = 300  # 5 minutes default
    
    # Cache unfiltered location-sorted pages at the client level (existing logic)
    if not query and sort_by == 'location':
        is_cacheable = True
        cache_duration = 300  # 5 minutes
    
    # Cache common text searches for anonymous users (NEW)
    elif query and not request.user.is_authenticated:
        # Cache common searches like "asda", "boots", "nottingham"
        common_searches = ['asda', 'boots', 'nottingham', 'tesco', 'sainsbury', 'morrisons']
        if query.lower() in common_searches or len(query) <= 10:
            is_cacheable = True
            cache_duration = 180  # 3 minutes for text searches
    
    # Cache technology and company filtered searches (NEW)
    elif (technology_filter or company_filter) and not query:
        is_cacheable = True
        cache_duration = 300  # 5 minutes for filtered searches
    
    if is_cacheable:
        # Set browser cache headers
        patch_cache_control(response, max_age=cache_duration, public=True)
        
        # Add ETag based on current data checksum
        current_checksum = static_cache.get_current_checksum()
        etag = f'"{current_checksum}-{page}-{query or "no-query"}"'
        response['ETag'] = etag
        
        # Add Last-Modified header
        response['Last-Modified'] = http_date(time_module.time())
        
        # Add Vary header for proper caching
        response['Vary'] = 'Accept-Encoding'
        
        logger.info(f"🌐 Added browser cache headers: max-age={cache_duration}, ETag={etag}")
    
    return response