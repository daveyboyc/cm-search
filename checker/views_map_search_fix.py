"""
Improved version of map_data_api for handling postcode searches
"""

def map_data_api(request):
    """
    Main map data API for fetching components by viewport and filters.
    Enhanced to better handle outward_code (postcode) searches.
    """
    # --- START: Performance Tracking ---
    import time, json, hashlib, re
    from django.core.cache import cache
    from django.db.models import Q 
    
    start_time = time.time()
    stage_times = {}
    
    def record_stage_time(stage):
        current = time.time()
        elapsed = current - start_time
        stage_times[stage] = elapsed
        return elapsed
    # --- END: Performance Tracking ---
    
    # --- START: Cache Handling ---
    params = request.GET.copy()
    search_query_param = params.get('q', '') or params.get('search_query', '')
    
    if search_query_param:
        # For search queries, especially postcode searches, we should not use cache
        # or we should use a very specific cache key that includes all search parameters
        print(f"MAP DATA API: Search query detected: '{search_query_param}', bypassing regular cache")
        cache_key = None  # Will skip cache for search queries
    else:
        # Normal operation - build cache key from parameters for non-search queries
        relevant_params = ['technology', 'north', 'south', 'east', 'west', 'company', 'year', 'cmu_id', 'detail_level', 'exact_technology', 'cm_period']
        filtered_params = {k: params.get(k, '') for k in relevant_params if k in params}
        params_string = json.dumps(sorted(filtered_params.items()))
        params_hash = hashlib.md5(params_string.encode('utf-8')).hexdigest()
        cache_key = f"map_data_{params_hash}"
        print(f"MAP DATA API: Generated cache key: '{cache_key}'")
    
    # Only check cache if we have a cache key
    cached_response = None
    if cache_key:
        cached_response = cache.get(cache_key)
        print(f"MAP DATA API: cache.get({cache_key}) returned: {type(cached_response)} (None means cache miss)")
    
    if cached_response and isinstance(cached_response, str):
        cache_time = record_stage_time("cache_check")
        print(f"✅ Cache HIT: Returning cached map data from Django cache for key: {cache_key}")
        
        # Return cached JSON string as HttpResponse
        from django.http import HttpResponse
        return HttpResponse(cached_response, content_type="application/json")
    # --- END: Cache Handling ---

    # --- START: Early exit if no filters ---
    technology_param_exists = 'technology' in request.GET
    company_filter = request.GET.get('company', '') 
    
    # Check for search query
    search_query = request.GET.get('q', '')
    if not search_query:
        search_query = request.GET.get('search_query', '')
    
    # Log all parameters for debugging
    print(f"MAP DATA API: Parameters: technology={technology_param_exists}, company='{company_filter}', search='{search_query}'")
    
    # Only require technology if no company or search query is present
    if not technology_param_exists and not company_filter and not search_query:
        empty_time = record_stage_time("early_exit")
        print(f"No search criteria provided. Returning empty results. (in {empty_time:.3f}s)")
        empty_response = {
            'type': 'FeatureCollection',
            'features': [],
            'metadata': { 'count': 0, 'total': 0, 'filtered': False }
        }
        from django.http import HttpResponse
        return HttpResponse(json.dumps(empty_response), content_type="application/json")
    # --- END: Early exit ---

    # --- Get detail level parameter ---
    detail_level = request.GET.get('detail_level', 'minimal')
    
    # --- START: Initial Query Builder ---
    from checker.models import Component
    
    # Always start with all components for search queries
    # This ensures we find matches even if they're not geocoded
    base_query = Component.objects.all()
    
    # --- START: Check for postcode search ---
    postcode_pattern = re.compile(r'^[A-Z]{1,2}[0-9][A-Z0-9]?$', re.IGNORECASE)
    is_postcode_search = False
    outward_code = None
    
    if search_query:
        # Clean up the search query for postcode matching
        clean_query = search_query.strip().upper().replace(' ', '')
        
        # Check if it matches the pattern for an outward code (e.g., SW11, E1, etc.)
        if postcode_pattern.match(clean_query):
            is_postcode_search = True
            outward_code = clean_query
            print(f"MAP DATA API: Detected postcode search for outward code: '{outward_code}'")
    # --- END: Check for postcode search ---
    
    # --- START: Apply Search Query Filter ---
    if search_query:
        print(f"MAP DATA API: Processing search query: '{search_query}'")
        
        if is_postcode_search and outward_code:
            # For postcode searches, prioritize outward_code field match
            print(f"MAP DATA API: Using outward_code filter for '{outward_code}'")
            base_query = base_query.filter(outward_code__iexact=outward_code)
            
            # Count results after outward_code filter
            outward_code_count = base_query.count()
            print(f"MAP DATA API: Found {outward_code_count} components with outward_code='{outward_code}'")
            
            # If no results with exact outward_code match, fall back to text search
            if outward_code_count == 0:
                print(f"MAP DATA API: No exact outward_code matches, using text search as fallback")
                base_query = Component.objects.all()  # Reset query
                
                # Use standard text search as fallback
                search_terms = search_query.split()
                query_filter_text_search = Q()
                for term in search_terms:
                    term_filter = (
                        Q(cmu_id__icontains=term) |
                        Q(company_name__icontains=term) |
                        Q(location__icontains=term) |
                        Q(description__icontains=term) |
                        Q(technology__icontains=term)
                    )
                    query_filter_text_search &= term_filter
                base_query = base_query.filter(query_filter_text_search)
        else:
            # Standard text search for non-postcode searches
            search_terms = search_query.split()
            query_filter_text_search = Q()
            for term in search_terms:
                term_filter = (
                    Q(cmu_id__icontains=term) |
                    Q(company_name__icontains=term) |
                    Q(location__icontains=term) |
                    Q(description__icontains=term) |
                    Q(technology__icontains=term)
                )
                query_filter_text_search &= term_filter
            base_query = base_query.filter(query_filter_text_search)
        
        # Log the count after text search filter
        text_search_count = base_query.count()
        print(f"MAP DATA API: Found {text_search_count} components matching search '{search_query}'")
    
    record_stage_time("search_filter")
    # --- END: Apply Search Query Filter ---
    
    # --- START: Apply Company Filter ---
    excluded_companies = ["AXLE ENERGY LIMITED", "OCTOPUS ENERGY LIMITED"]
    
    if company_filter: 
        # Filter for specific company
        base_query = base_query.filter(company_name=company_filter)
        print(f"Applied company filter: {company_filter}")
    else:
        # Default: exclude certain companies
        base_query = base_query.exclude(company_name__in=excluded_companies)
        print(f"Applied default company exclusion: {excluded_companies}")
    # --- END: Apply Company Filter ---
    
    # --- START: Apply Year and Technology Filters ---
    specific_year_requested = request.GET.get('year')
    requested_technology = request.GET.get('technology')
    exact_technology = request.GET.get('exact_technology')
    cm_period = request.GET.get('cm_period', 'future')
    
    is_filtered = search_query != ''  # Start with true if search query exists
    
    # Apply Year Filters if needed
    if specific_year_requested:
        if specific_year_requested.isdigit() and len(specific_year_requested) == 4:
            base_query = base_query.filter(delivery_year__iexact=specific_year_requested)
            print(f"Applied specific year filter: {specific_year_requested}")
            is_filtered = True
        else:
            print(f"Ignoring invalid year format: {specific_year_requested}")
    else:
        # Apply filter based on CM period (unless search query is present)
        if not search_query:
            if cm_period == 'historical':
                base_query = base_query.filter(
                    Q(delivery_year__gte='2016') & Q(delivery_year__lte='2023')
                )
                print("Applied historical CM period filter: 2016-2023")
            else:
                base_query = base_query.filter(Q(delivery_year__gte='2024'))
                print("Applied future CM period filter: >= 2024")
    
    # Apply Technology Filter if needed
    if requested_technology and requested_technology != 'All':
        is_filtered = True
        if exact_technology:
            print(f"Using exact technology filter: '{exact_technology}'")
            base_query = base_query.filter(technology=exact_technology)
        else:
            # Implement simplified technology filtering
            # ...code here to match technologies by category...
            pass
    
    record_stage_time("standard_filters")
    # --- END: Apply Year and Technology Filters ---
    
    # --- START: Apply Viewport Filter ---
    north = request.GET.get('north')
    south = request.GET.get('south')
    east = request.GET.get('east')
    west = request.GET.get('west')
    
    viewport_filtered = False
    
    # Skip viewport filtering for search queries
    if search_query:
        print(f"MAP DATA API: Skipping viewport filtering for search query: '{search_query}'")
    elif north and south and east and west:
        try:
            north_f, south_f, east_f, west_f = map(float, [north, south, east, west])
            if -90 <= south_f < north_f <= 90 and -180 <= west_f <= 180 and -180 <= east_f <= 180:
                print(f"Applying viewport filter: N:{north_f}, S:{south_f}, E:{east_f}, W:{west_f}")
                if west_f <= east_f:
                    base_query = base_query.filter(
                        latitude__lte=north_f, latitude__gte=south_f,
                        longitude__lte=east_f, longitude__gte=west_f
                    )
                else: # Viewport crosses the dateline
                    base_query = base_query.filter(
                        latitude__lte=north_f, latitude__gte=south_f
                    ).filter(
                        Q(longitude__gte=west_f) | Q(longitude__lte=east_f)
                    )
                viewport_filtered = True
                is_filtered = True
            else:
                print("Invalid bounds received, skipping viewport filter.")
        except ValueError:
            print("Error parsing bounds, skipping viewport filter.")
    
    record_stage_time("viewport_filter")
    # --- END: Apply Viewport Filter ---
    
    # --- START: Count and Process Results ---
    # Get total count before applying limits
    total_matching_components = base_query.count()
    count_time = record_stage_time("count_calculation")
    print(f"Total matching components after filters: {total_matching_components}")
    
    # Apply limit for GeoJSON features
    requested_limit_str = request.GET.get('limit', '5000')
    try:
        requested_limit = int(requested_limit_str)
        limit = 10000 if viewport_filtered else requested_limit
    except ValueError:
        limit = 10000 if viewport_filtered else 5000
    
    print(f"Using limit: {limit}")
    
    # Select fields based on detail level
    if detail_level == 'minimal':
        fields_to_fetch = ('id', 'latitude', 'longitude', 'technology', 'location')
    else:
        fields_to_fetch = ('id', 'latitude', 'longitude', 'location',
                          'company_name', 'description', 'technology', 
                          'delivery_year', 'cmu_id')
    
    # Get components to render
    components_to_render = base_query.values(*fields_to_fetch)[:limit]
    query_time = record_stage_time("db_query")
    print(f"Query executed in {query_time - count_time:.3f}s, fetched {len(components_to_render)} components")
    
    # Count geocoded vs non-geocoded components
    geocoded_count = 0
    non_geocoded_count = 0
    
    # Group components by coordinates
    components_by_coord = {}
    for comp in components_to_render:
        lat = comp.get('latitude')
        lng = comp.get('longitude')
        
        # Check geocoding status
        if lat is not None and lng is not None:
            geocoded_count += 1
            
            # Only add to map if it has coordinates
            coord_key = (lat, lng)
            if coord_key not in components_by_coord:
                components_by_coord[coord_key] = []
            components_by_coord[coord_key].append(comp)
        else:
            non_geocoded_count += 1
    
    print(f"MAP DATA API: {geocoded_count} geocoded and {non_geocoded_count} non-geocoded components")
    print(f"Grouped into {len(components_by_coord)} unique coordinates")
    
    # For postcode searches, create a special marker if no geocoded results
    features = []
    
    if is_postcode_search and geocoded_count == 0 and outward_code:
        # No geocoded results for this postcode search - create a fallback marker
        print(f"MAP DATA API: Creating fallback marker for '{outward_code}' with no geocoded results")
        
        # Get approximate coordinates for common London postcodes
        fallback_coords = {
            'SW11': {'lat': 51.47, 'lng': -0.16},  # Battersea
            'SW1': {'lat': 51.50, 'lng': -0.14},   # Westminster
            'E1': {'lat': 51.52, 'lng': -0.07},    # Whitechapel
            'N1': {'lat': 51.54, 'lng': -0.10},    # Islington
            'SE1': {'lat': 51.50, 'lng': -0.10},   # Southwark
        }
        
        coords = fallback_coords.get(outward_code, {'lat': 51.50, 'lng': -0.12})  # Default to central London
        
        # Create a special feature for the fallback marker
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [coords['lng'], coords['lat']]
            },
            'properties': {
                'id': 0,
                'cmu_id': '',
                'title': f'{outward_code} - Approximate Location',
                'technology': 'Unknown',
                'display_technology': 'Unknown',
                'company': '',
                'description': f'No geocoded components found for {outward_code}',
                'delivery_year': '',
                'detailUrl': '/',
                'is_fallback': True
            }
        })
    
    # Build GeoJSON features from grouped components
    for coord, grouped_components in components_by_coord.items():
        if not grouped_components: 
            continue
        
        representative_comp = grouped_components[0]
        
        # Get simplified technology (for visualization)
        from checker.views import get_simplified_technology
        simplified_tech = get_simplified_technology(representative_comp.get('technology', 'Unknown'))
        
        # Create feature properties
        feature_properties = {
            'id': representative_comp['id'],
            'cmu_id': representative_comp.get('cmu_id', ''),
            'title': representative_comp.get('location', 'Unknown Location'),
            'technology': representative_comp.get('technology', 'Unknown'),
            'display_technology': simplified_tech,
            'company': representative_comp.get('company_name', 'Unknown'),
            'description': representative_comp.get('description', ''),
            'delivery_year': representative_comp.get('delivery_year', ''),
            'detailUrl': f'/component/{representative_comp["id"]}/'
        }
        
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [coord[1], coord[0]]  # longitude, latitude
            },
            'properties': feature_properties
        })
    
    json_build_time = record_stage_time("json_build")
    # --- END: Count and Process Results ---
    
    # --- START: Build Response ---
    # Determine if the response is filtered
    final_is_filtered = any([
        search_query != '',
        requested_technology not in ['', 'All'],
        company_filter != '',
        specific_year_requested is not None,
        viewport_filtered
    ])
    
    # Build the GeoJSON response
    response_data = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'count': len(features),
            'total': total_matching_components,
            'filtered': final_is_filtered,
            'geocoded_count': geocoded_count,
            'non_geocoded_count': non_geocoded_count,
            'is_postcode_search': is_postcode_search,
            'outward_code': outward_code if is_postcode_search else None
        }
    }
    
    total_time = record_stage_time("total")
    print(f"Returning {len(features)} features (total matches: {total_matching_components})")
    print(f"--- map_data_api processing completed in {total_time:.3f}s ---")
    
    # Create JSON string from response data
    from django.http import HttpResponse
    json_str = json.dumps(response_data)
    
    # Cache the result if we have a cache key
    if cache_key:
        try:
            cache.set(cache_key, json_str, 3600)  # Cache for 1 hour
            print(f"DEBUG: Cached response with key '{cache_key}'")
        except Exception as e:
            print(f"DEBUG ERROR: Failed to cache data: {e}")
    
    # Return JSON response
    return HttpResponse(json_str, content_type="application/json")