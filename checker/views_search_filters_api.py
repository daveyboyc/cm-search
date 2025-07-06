"""
AJAX API for lazy loading search dropdown filters
Provides relevant filter options based on search results
"""
import time
import logging
import hashlib
from django.http import JsonResponse
from django.db.models import Q
from django.db import connection
from django.core.cache import cache
from .models import LocationGroup
from .services.postcode_helpers import get_all_postcodes_for_area
from .decorators.access_required import map_access_required

logger = logging.getLogger(__name__)

@map_access_required
def search_filters_api(request):
    """
    AJAX endpoint to get relevant filter options for search results, technology pages, company pages, and CMU pages
    Returns JSON with technologies, companies, and auction years
    
    Supported parameters:
    - q: General search query
    - technology: Technology-specific filters
    - company: Company-specific filters
    - cmu: CMU-specific filters
    """
    start_time = time.time()
    
    # Get parameters
    query = request.GET.get('q', '').strip()
    technology_name = request.GET.get('technology', '').strip()
    company_name = request.GET.get('company', '').strip()
    cmu_id = request.GET.get('cmu', '').strip()
    
    # Handle empty query (all locations) - should return all available filters
    if not any([query, technology_name, company_name, cmu_id]):
        # For "all locations", treat as if searching all LocationGroups
        query = ""  # Empty query means all locations
    
    try:
        # Create cache key for this specific request
        cache_params = f"{query}|{technology_name}|{company_name}|{cmu_id}"
        cache_key = f"filter_api_{hashlib.md5(cache_params.encode()).hexdigest()[:12]}"
        
        # Try to get cached result first
        cached_result = cache.get(cache_key)
        if cached_result:
            cached_result['load_time'] = time.time() - start_time
            cached_result['cached'] = True
            logger.info(f"🚀 Cached filter result returned in {cached_result['load_time']:.3f}s")
            return JsonResponse(cached_result)
        
        # Handle different types of filter requests
        location_groups = None
        
        if technology_name:
            # Technology page filters
            import urllib.parse
            technology_display = urllib.parse.unquote(technology_name)
            
            # Special handling for Interconnector umbrella category
            if technology_display.lower() == 'interconnector':
                interconnector_techs = [
                    'BritNed', 'ElecLink', 'EWIC', 'Greenlink', 'IFA', 'IFA2', 
                    'Moyle', 'Nemo', 'NeuConnect', 'NSL', 'VikingLink'
                ]
                interconnector_query = Q()
                for tech_name in interconnector_techs:
                    interconnector_query |= Q(technologies__has_key=tech_name)
                location_groups = LocationGroup.objects.filter(interconnector_query)
            else:
                location_groups = LocationGroup.objects.filter(technologies__icontains=technology_display)
                
        elif company_name:
            # Company page filters
            import urllib.parse
            company_display = urllib.parse.unquote(company_name)
            location_groups = LocationGroup.objects.filter(companies__has_key=company_display)
            
        elif cmu_id:
            # CMU page filters
            location_groups = LocationGroup.objects.filter(cmu_ids__icontains=cmu_id)
            
        elif query:
            # General search filters (existing logic)
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
                    # Multi-word search: use AND logic for regular searches
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
                        location_filter &= part_filter
                    
                    location_groups = LocationGroup.objects.filter(location_filter)
                else:
                    # Single word search - prioritize direct matches
                    direct_matches = LocationGroup.objects.filter(
                        Q(location__icontains=query) |
                        Q(county__icontains=query) |
                        Q(companies__icontains=query) |
                        Q(technologies__icontains=query) |
                        Q(descriptions__icontains=query) |
                        Q(cmu_ids__icontains=query)
                    )
                    
                    # Check if it's a postcode-based search with smart area detection
                    area_postcodes = get_all_postcodes_for_area(query)
                    is_legitimate_area = False
                    
                    if area_postcodes:
                        # Allow if it's a real postcode (contains digits)
                        if any(c.isdigit() for c in query):
                            is_legitimate_area = True
                        # Allow major UK cities and known areas
                        elif query.lower() in ['london', 'birmingham', 'manchester', 'glasgow', 'edinburgh', 'cardiff', 'belfast',
                                             'peckham', 'battersea', 'hackney', 'islington', 'camden', 'greenwich', 'lambeth',
                                             'southwark', 'tower hamlets', 'newham', 'barking', 'croydon', 'bromley', 'bexley']:
                            is_legitimate_area = True
                        # Allow if reasonable postcodes AND looks like UK place name
                        elif (area_postcodes and 
                              any(pc.startswith(('SW', 'SE', 'E', 'N', 'W', 'EC', 'WC', 'NW', 'B', 'M', 'G')) for pc in area_postcodes) and
                              len(query) >= 5 and
                              query.lower().endswith(('ham', 'sea', 'ton', 'ford', 'wich', 'stead', 'field', 'bridge', 'green', 'hill', 'park'))):
                            is_legitimate_area = True
                    
                    if is_legitimate_area and direct_matches.count() < 10:
                        postcode_filter = Q()
                        for postcode in area_postcodes:
                            postcode_filter |= Q(outward_code=postcode)
                        
                        area_groups = LocationGroup.objects.filter(postcode_filter)
                        location_groups = direct_matches | area_groups
                        location_groups = location_groups.distinct()
                    else:
                        location_groups = direct_matches
        else:
            # Empty query means "all locations" - use optimized approach
            # Instead of filtering, directly get all unique values from the database
            logger.info("🚀 All locations filter request - using optimized direct queries")
            
            with connection.cursor() as cursor:
                # Get all unique technologies directly
                cursor.execute("""
                    SELECT DISTINCT jsonb_object_keys(technologies) as tech
                    FROM checker_locationgroup 
                    WHERE technologies IS NOT NULL
                    ORDER BY tech
                    LIMIT 200
                """)
                technologies = [row[0] for row in cursor.fetchall()]
                
                # Get all unique companies directly
                cursor.execute("""
                    SELECT DISTINCT jsonb_object_keys(companies) as company
                    FROM checker_locationgroup 
                    WHERE companies IS NOT NULL
                    ORDER BY company
                    LIMIT 300
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
            
            # Skip the expensive filtering logic and return results immediately
            load_time = time.time() - start_time
            logger.info(f"🚀 All locations filters loaded directly in {load_time:.3f}s")
            
            # Prepare response
            response_data = {
                'technologies': technologies,
                'companies': companies,
                'auction_years': auction_years,
                'total_results': 'all',  # Indicate this is all data
                'load_time': load_time,
                'cached': False
            }
            
            # Cache the result for 10 minutes (all locations filters change rarely)
            cache.set(cache_key, response_data, timeout=600)  # 10 minutes - reduce network egress
            
            return JsonResponse(response_data)
        
        # OPTIMIZED: Limit processing to first 500 results for performance
        # This gives us comprehensive filter coverage without processing thousands of rows
        limited_groups = location_groups[:500] if location_groups else []
        base_ids = [lg.id for lg in limited_groups]
        
        if base_ids:
            with connection.cursor() as cursor:
                # OPTIMIZED: Use LIMIT in subqueries for faster processing
                # Get unique technologies (limit to top 100 for UI performance)
                cursor.execute("""
                    SELECT DISTINCT tech
                    FROM (
                        SELECT jsonb_object_keys(technologies) as tech
                        FROM checker_locationgroup 
                        WHERE id = ANY(%s) AND technologies IS NOT NULL
                        LIMIT 1000
                    ) t
                    ORDER BY tech
                    LIMIT 100
                """, [base_ids])
                technologies = [row[0] for row in cursor.fetchall()]
                
                # Get unique companies (limit to top 200 for UI performance) 
                cursor.execute("""
                    SELECT DISTINCT company
                    FROM (
                        SELECT jsonb_object_keys(companies) as company
                        FROM checker_locationgroup 
                        WHERE id = ANY(%s) AND companies IS NOT NULL
                        LIMIT 1000
                    ) c
                    ORDER BY company
                    LIMIT 200
                """, [base_ids])
                companies = [row[0] for row in cursor.fetchall()]
                
                # Get unique auction years (limit to top 50 for UI performance)
                cursor.execute("""
                    SELECT DISTINCT year
                    FROM (
                        SELECT jsonb_array_elements_text(auction_years) as year
                        FROM checker_locationgroup 
                        WHERE id = ANY(%s) AND auction_years IS NOT NULL
                        LIMIT 500
                    ) y
                    ORDER BY year DESC
                    LIMIT 50
                """, [base_ids])
                auction_years = [row[0] for row in cursor.fetchall()]
        else:
            technologies = []
            companies = []
            auction_years = []
        
        load_time = time.time() - start_time
        
        # Log different types of requests
        if technology_name:
            logger.info(f"🔄 Technology filter API for '{technology_name}': {len(technologies)} techs, {len(companies)} companies, {len(auction_years)} years in {load_time:.3f}s")
        elif company_name:
            logger.info(f"🔄 Company filter API for '{company_name}': {len(technologies)} techs, {len(companies)} companies, {len(auction_years)} years in {load_time:.3f}s")
        elif cmu_id:
            logger.info(f"🔄 CMU filter API for '{cmu_id}': {len(technologies)} techs, {len(companies)} companies, {len(auction_years)} years in {load_time:.3f}s")
        else:
            logger.info(f"🔄 Search filter API for '{query}': {len(technologies)} techs, {len(companies)} companies, {len(auction_years)} years in {load_time:.3f}s")
        
        # Prepare response
        response_data = {
            'technologies': technologies,
            'companies': companies,
            'auction_years': auction_years,
            'total_results': len(base_ids),
            'load_time': load_time,
            'cached': False
        }
        
        # Cache the result for 5 minutes (filters don't change often)
        cache.set(cache_key, response_data, timeout=300)  # 5 minutes - reduce network egress
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Filter API error for query '{query}': {e}")
        return JsonResponse({
            'error': 'Failed to load filters',
            'technologies': [],
            'companies': [],
            'auction_years': [],
            'load_time': time.time() - start_time
        }, status=500)