"""
Search GeoJSON API endpoint for map visualization using LocationGroup
"""
from django.http import JsonResponse
from django.db.models import Q
from checker.models import LocationGroup
import time
import urllib.parse
import json
# Monitoring import
try:
    from monitoring.decorators import monitor_api
except ImportError:
    # Fallback if monitoring is not available
    def monitor_api(func):
        return func

from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from django.core.cache import cache
from .decorators.access_required import map_access_required

@monitor_api
@gzip_page
@map_access_required
def search_results_geojson(request):
    """
    Return search results as GeoJSON for map display.
    Uses LocationGroup for aggregated location data.
    """
    # Track performance
    start_time = time.time()
    
    # DEBUG: Log all request parameters
    query_params = dict(request.GET.items())
    print(f"🔍 GeoJSON API Request: {request.method} {request.path}")
    print(f"📊 Query Parameters: {query_params}")
    print(f"🕐 Request Start Time: {time.strftime('%H:%M:%S', time.localtime(start_time))}")
    
    # Implement intelligent caching: only cache non-viewport requests
    has_viewport = any(request.GET.get(param) for param in ['north', 'south', 'east', 'west'])
    
    if not has_viewport:
        # Create cache key for static requests (no viewport bounds)
        cache_params = []
        for param in ['q', 'tech', 'subtype', 'company', 'show_active', 'residential', 'limit']:
            value = request.GET.get(param, '')
            if value:
                cache_params.append(f"{param}={value}")
        
        cache_key = f"geojson_static:{'&'.join(cache_params) if cache_params else 'empty'}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            print(f"🚀 Cache HIT for static GeoJSON request")
            return JsonResponse(cached_response)
        
        print(f"⏱️  Cache MISS for static GeoJSON request: {cache_key}")
    else:
        print(f"🗺️  Viewport request - no caching to prevent Redis bloat")
    
    # Get search query and any parameters
    search_query = request.GET.get('q', '')
    tech_filter = request.GET.get('tech', '')
    subtype_filter = request.GET.get('subtype', '')  # For DSR subtypes: Octopus, Axle, Everything else
    company_filter = request.GET.get('company', '')  # New company filter for map explorer
    show_active_param = request.GET.get('show_active', 'true').lower()
    # Handle 'all' case by checking if parameter was explicitly provided
    show_all = 'show_active' not in request.GET  # If parameter not provided, show all
    show_active = show_active_param == 'true' if not show_all else None
    # Viewport and clustering parameters
    limit = int(request.GET.get('limit', 200))  # Default to 200 for performance
    north = request.GET.get('north')  # Viewport bounds
    south = request.GET.get('south')
    east = request.GET.get('east')
    west = request.GET.get('west')
    zoom_level = int(request.GET.get('zoom', 0))  # Current zoom level
    
    # Allow empty queries to show all results (for map explorer)
    # Only return empty if both query and tech filter are missing AND no limit specified
    if not search_query and not tech_filter and limit == 1000:
        # For map explorer, we want to show some results even with empty query
        # Return a sample of active locations
        pass  # Continue to process the query
    
    # Build query for LocationGroups
    location_groups = LocationGroup.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Apply viewport bounds filtering EARLY for performance
    # This is critical for large datasets like Octopus DSR
    viewport_applied = False
    if north and south and east and west:
        try:
            north_f = float(north)
            south_f = float(south)
            east_f = float(east)
            west_f = float(west)
            
            location_groups = location_groups.filter(
                latitude__gte=south_f,
                latitude__lte=north_f,
                longitude__gte=west_f,
                longitude__lte=east_f
            )
            viewport_applied = True
            print(f"🎯 Viewport bounds applied: N:{north_f:.2f} S:{south_f:.2f} E:{east_f:.2f} W:{west_f:.2f}")
        except ValueError:
            # Invalid bounds, skip filtering
            print(f"⚠️ Invalid viewport bounds provided")
            pass
    
    # Apply active/inactive filter based on toggle state
    # When show_active=true, show active locations
    # When show_active=false, show inactive locations  
    # When show_active parameter not provided, show all locations
    if show_active is True:
        location_groups = location_groups.filter(is_active=True)
    elif show_active is False:
        location_groups = location_groups.filter(is_active=False)
    # If show_active is None (show_all case), don't filter by active status
    
    # Handle search query
    if search_query:
        # Check if this is a CMU ID search
        if search_query.upper().startswith(('CMU', 'BMU', 'DSR')):
            # Search in the cmu_ids JSON field
            location_groups = location_groups.filter(cmu_ids__contains=search_query.upper())
        else:
            # Text search across location name and descriptions
            search_terms = search_query.split()
            for term in search_terms:
                # Search in both location name and descriptions using Q objects
                from django.db.models import Q
                location_groups = location_groups.filter(
                    Q(location__icontains=term) | Q(descriptions__icontains=term)
                )
    
    # Handle technology filter
    if tech_filter and tech_filter != 'All':
        # OPTIMIZED: Build all technology variations upfront at database level
        tech_variations = {
            'CHP': ['CHP', 'Combined Heat and Power (CHP)', 'CHP and autogeneration'],
            'DSR': ['DSR', 'Demand Side Response'],
            'EV Charging': ['EV Charging'],
            'Battery': ['Battery', 'Battery Storage', 'Battery storage', 'Storage', 'Storage (Duration 0.5h)', 'Storage (Duration 1h)', 'Storage (Duration 1.5h)', 'Storage (Duration 2h)', 'Storage (Duration 2.5h)', 'Storage (Duration 3h)', 'Storage (Duration 3.5h)', 'Storage (Duration 4h)', 'Storage (Duration 4.5h)', 'Storage (Duration 5h)', 'Storage (Duration 5.5h)', 'Storage (Duration 6h)', 'Storage (Duration 7h)', 'Storage (Duration 8h)', 'Storage (Duration 8.5h)', 'Storage (Duration 9h)', 'Storage (Duration 9.5h)', 'Storage (Duration 12h)'],
            'OCGT': ['Gas', 'Gas - OCGTs and reciprocating engines', 'Gas reciprocating engines', 'OCGT', 'Combined Cycle Gas Turbine (CCGT)', 'Open Cycle Gas Turbine (OCGT)', 'OCGT and Reciprocating Engines', 'OCGT and Reciprocating Engines (Fuel Type - Diesel)', 'OCGT and Reciprocating Engines (Fuel Type - Gas)', 'Reciprocating engines'],
            'Wind': ['Wind', 'Onshore Wind', 'Offshore Wind'],
            'Solar': ['Solar', 'Solar Photovoltaic'],
            'Nuclear': ['Nuclear'],
            'Hydro': ['Hydro', 'Hydro Power', 'Pumped Storage Hydro'],
            'Biomass': ['Biomass', 'Energy from Waste', 'Coal/biomass'],
            'Interconnector': ['Interconnector', 'Interconnection', 'BritNED (Netherlands)', 'Eleclink (France)', 'EWIC (Ireland)', 'EWIC (Republic of Ireland)', 'Greenlink (Republic of Ireland)', 'IFA2 (France)', 'IFA (France)', 'Moyle (Northern Ireland)', 'NEMO (Belgium)', 'NeuConnect (Germany)', 'NSL (Norway)', 'VikingLink (Denmark)'],
            'Coal': ['Coal']
        }
        
        # Build Q objects for all variations - do this ONCE at database level
        from django.db.models import Q
        q_filter = Q()
        
        # Check if we have variations for this tech
        if tech_filter in tech_variations:
            # For performance, use a single query with OR conditions
            variations = tech_variations[tech_filter]
            for variation in variations:
                q_filter |= Q(technologies__has_key=variation)
        else:
            # Direct filter for unknown techs
            q_filter = Q(technologies__has_key=tech_filter)
            
        location_groups = location_groups.filter(q_filter)
    
    # Handle DSR subtype filtering (Octopus, Axle, Everything else)
    if tech_filter == 'DSR' and subtype_filter:
        from django.db.models import Q
        if subtype_filter == 'Octopus':
            # Show only Octopus Energy DSR
            location_groups = location_groups.filter(companies__has_key='OCTOPUS ENERGY LIMITED')
        elif subtype_filter == 'Axle':
            # Show only Axle Energy DSR
            location_groups = location_groups.filter(companies__has_key='AXLE ENERGY LIMITED')
        elif subtype_filter == 'Everything else':
            # Show all DSR except Octopus and Axle (current default DSR behavior)
            exclude_query = Q()
            exclude_query |= Q(companies__has_key='OCTOPUS ENERGY LIMITED')
            exclude_query |= Q(companies__has_key='AXLE ENERGY LIMITED')
            location_groups = location_groups.exclude(exclude_query)
    
    # Handle residential DSR filtering
    residential_filter = request.GET.get('residential', '')
    if residential_filter:
        # If residential DSR filter is specified, only show that specific company
        location_groups = location_groups.filter(companies__has_key=residential_filter)
    # Skip residential exclusion entirely if a specific company is already selected
    # This optimizes queries for Octopus/Axle + DSR/EV Charging combinations
    elif not company_filter and not ((tech_filter == 'DSR' and subtype_filter)):
        # Only exclude residential companies if NO company is selected
        # and NOT using DSR subtypes
        residential_companies = ['AXLE ENERGY LIMITED', 'OCTOPUS ENERGY LIMITED']
        from django.db.models import Q
        exclude_query = Q()
        for company in residential_companies:
            exclude_query |= Q(companies__has_key=company)
        location_groups = location_groups.exclude(exclude_query)
    
    # Handle company filter (for map explorer)
    if company_filter:
        if company_filter == 'Everything else':
            # "Everything else" - show only companies with ≤7 locations
            # First get list of companies with >7 locations to exclude
            from django.db import connection
            from django.db.models import Q
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    WITH location_counts AS (
                        SELECT 
                            jsonb_object_keys(lg.companies) as company_name,
                            COUNT(DISTINCT lg.id) as location_count
                        FROM checker_locationgroup lg
                        WHERE lg.companies IS NOT NULL
                        GROUP BY jsonb_object_keys(lg.companies)
                    )
                    SELECT company_name
                    FROM location_counts
                    WHERE company_name IS NOT NULL
                    AND company_name != ''
                    AND location_count > 7
                """)
                
                big_companies = [row[0] for row in cursor.fetchall()]
            
            # Exclude all companies with >7 locations
            exclude_query = Q()
            for company in big_companies:
                exclude_query |= Q(companies__has_key=company)
            location_groups = location_groups.exclude(exclude_query)
        else:
            # Filter locations that have the specified company
            # The companies field is a JSON dict like {"Company Name": 3, "Another Company": 1}
            # Handle case-insensitive matching by checking all variations
            from django.db.models import Q
            company_filter_upper = company_filter.upper()
            company_filter_lower = company_filter.lower()
            company_filter_title = company_filter.title()
            
            # Try multiple case variations to handle data inconsistencies
            company_query = (
                Q(companies__has_key=company_filter) |  # Exact match
                Q(companies__has_key=company_filter_upper) |  # UPPER CASE
                Q(companies__has_key=company_filter_lower) |  # lower case
                Q(companies__has_key=company_filter_title)  # Title Case
            )
            location_groups = location_groups.filter(company_query)
    
    # PERFORMANCE OPTIMIZATION: Skip count for Octopus/Axle queries
    # These queries are too slow and cause timeouts
    is_octopus_axle_query = (
        (company_filter in ['OCTOPUS ENERGY LIMITED', 'AXLE ENERGY LIMITED']) or
        (tech_filter == 'DSR' and subtype_filter in ['Octopus', 'Axle']) or
        (tech_filter == 'EV Charging' and subtype_filter in ['Octopus', 'Axle'])
    )
    
    if is_octopus_axle_query:
        # Skip the expensive count query for Octopus/Axle
        total_count = -1  # Sentinel value to indicate count was skipped
        print(f"⚡ Skipping count query for Octopus/Axle (known to be 6400+ results)")
    else:
        # Get total count before limiting
        count_start = time.time()
        total_count = location_groups.count()
        count_duration = time.time() - count_start
        print(f"📈 Count Query: {total_count} results in {count_duration:.3f}s")
    
    # For map explorer, allow sampling of large result sets
    # Always show results up to the limit, rather than rejecting large searches
    if total_count > limit:
        # Log sampling for monitoring
        pass  # Sampling large result set for performance
    
    # For viewport queries with Octopus/Axle, we can show more results
    # since the viewport already limits the data
    if is_octopus_axle_query and not viewport_applied:
        # Only limit non-viewport queries to prevent timeout
        limit = min(limit, 100)
        print(f"🚨 Large Octopus/Axle query - limiting to {limit} for Heroku compatibility")
    elif is_octopus_axle_query and viewport_applied:
        # For viewport queries, allow more results since they're geographically limited
        limit = min(limit, 200)
        print(f"🎯 Octopus/Axle viewport query - allowing up to {limit} results")
    
    # Apply smart ordering based on zoom level
    if zoom_level > 10:
        # High zoom: prioritize by capacity (show important locations first)
        location_groups = location_groups.order_by('-normalized_capacity_mw', 'location')
    else:
        # Low zoom: use ID-based ordering for performance (pseudo-random distribution)
        # Random ordering with '?' is very slow in PostgreSQL
        location_groups = location_groups.order_by('id')
    
    # Apply limit and OPTIMIZE: Only fetch fields needed for GeoJSON (60-80% egress reduction)
    query_start = time.time()
    
    # For Octopus/Axle queries, defer only the largest unused fields that actually exist
    if is_octopus_axle_query:
        location_groups = location_groups.defer(
            'capacity_calculation_notes', 'created_at', 'updated_at'
        ).select_related('representative_component')[:limit]
    else:
        location_groups = location_groups.only(
            'id', 'location', 'latitude', 'longitude', 'outward_code',
            'technologies', 'companies', 'component_count', 'normalized_capacity_mw',
            'is_active', 'representative_component_id', 'auction_years', 'cmu_ids', 'descriptions'
        ).select_related('representative_component')[:limit]
    
    # Force evaluation of queryset
    location_list = list(location_groups)
    data_duration = time.time() - query_start
    print(f"💾 Data Query: {len(location_list)} locations fetched in {data_duration:.3f}s")
    
    # Convert LocationGroups to GeoJSON features
    features = []
    
    # Simplified processing for better performance
    
    for location_group in location_list:
        # Get the technology to display based on filter
        technologies = location_group.technologies or {}
        
        if tech_filter and tech_filter != 'All':
            # OPTIMIZED: Since filtering is now done at database level, 
            # we know this location has the filtered technology
            # Just find the best matching tech name from the location's technologies
            dominant_tech = tech_filter
            
            # Try to find the exact technology name in this location
            for tech_name in technologies.keys():
                if tech_name == tech_filter:
                    dominant_tech = tech_name
                    break
                # For display purposes, prefer the more specific technology name
                if tech_filter == 'OCGT' and 'Open Cycle Gas Turbine (OCGT)' in tech_name:
                    dominant_tech = tech_name
                    break
                elif tech_filter == 'Battery' and 'Storage (Duration' in tech_name:
                    dominant_tech = tech_name
                    break
        else:
            # No specific filter, use the location's primary technology with priority logic
            dominant_tech = location_group.get_primary_technology()
            
            # Skip debug logging for performance
        
        # Get the latest auction year
        auction_years = location_group.auction_years or []
        latest_auction = auction_years[0] if auction_years else ''
        
        # Simple description handling for performance
        descriptions = location_group.descriptions or []
        first_description = descriptions[0] if descriptions else ''
        
        # Skip expensive description analysis for performance
        
        # Get first CMU ID for display
        cmu_ids_data = location_group.cmu_ids or {}
        if isinstance(cmu_ids_data, dict) and 'sample' in cmu_ids_data:
            cmu_ids_list = cmu_ids_data['sample']
            display_cmu_id = cmu_ids_list[0] if cmu_ids_list else ''
        elif isinstance(cmu_ids_data, list):
            display_cmu_id = cmu_ids_data[0] if cmu_ids_data else ''
        else:
            display_cmu_id = ''
        
        # Get company with most components - use optimized method
        # When a company filter is active, show the filtered company instead of dominant
        if company_filter and company_filter != 'Everything else':
            # Use the filtered company name
            dominant_company = company_filter
        else:
            # Use the location's primary company
            dominant_company = location_group.get_primary_company()
        
        # Skip debug logging for performance
        
        # Create GeoJSON feature - OPTIMIZED for minimal egress
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [location_group.longitude, location_group.latitude]
            },
            'properties': {
                'id': location_group.id,
                'title': location_group.location,
                'tech': dominant_tech,  # Shortened for bandwidth
                'company': dominant_company,
                'desc': first_description[:100] + ('...' if len(first_description) > 100 else ''),  # Truncate long descriptions
                'cmu': display_cmu_id,
                'url': f'/location/{location_group.id}/',  # Direct link to location group detail
                'count': location_group.component_count,
                'active': location_group.is_active,
                'mw': location_group.normalized_capacity_mw or 0
            }
        }
        features.append(feature)
    
    # Create GeoJSON response
    response_data = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'count': len(features),
            'total': total_count if total_count != -1 else len(features),  # Use feature count if total was skipped
            'geocoded_count': len(features),  # All LocationGroups have coordinates
            'non_geocoded_count': 0,
            'query': search_query or tech_filter,
            'technology_filter': tech_filter,
            'processing_time': f"{(time.time() - start_time):.3f}s",
            'grouped_by_location': True,
            'using_location_groups': True,  # Flag to indicate new data source
            'display_note': "Showing aggregated location data" + (" (limited for performance)" if is_octopus_axle_query else ""),
            'max_results': limit,
            'viewport': {
                'has_bounds': bool(north and south and east and west),
                'zoom_level': zoom_level,
                'showing_sample': total_count == -1 or total_count > len(features)
            }
        }
    }
    
    # Cache static requests (no viewport bounds) to reduce Redis bloat
    if not has_viewport:
        cache.set(cache_key, response_data, 60 * 5)  # Cache for 5 minutes (reduced to save Redis memory)
        print(f"💾 Cached static GeoJSON response for 5 minutes")
    
    total_duration = time.time() - start_time
    print(f"✅ GeoJSON Response: {len(features)} features, {total_duration:.3f}s total")
    print(f"🔚 Response End Time: {time.strftime('%H:%M:%S', time.localtime())}")
    
    return JsonResponse(response_data)