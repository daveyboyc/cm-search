"""
Batch API endpoints for optimized map data loading.

This module provides batched API endpoints that can handle multiple
technology requests in a single call, reducing the number of sequential
API calls and improving map loading performance.
"""
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from django.db.models import Q
from django.core.cache import cache
import json
import time
import logging

from .models import LocationGroup
from .services.map_cache import get_cached_map_data, cache_map_data, generate_map_cache_key
from .decorators.access_required import map_access_required

logger = logging.getLogger(__name__)


@map_access_required
@gzip_page
def batch_geojson_api(request):
    """
    Batch API endpoint that can handle multiple technology requests in a single call.
    
    Parameters:
    - tech[]: Array of technology names (e.g., ?tech[]=OCGT&tech[]=Wind&tech[]=Solar)
    - q: Search query (optional)
    - north, south, east, west: Viewport bounds
    - show_active: Filter for active/inactive components (default: true)
    - limit: Maximum results per technology (default: 1000)
    
    Returns:
    JSON response with results for each requested technology.
    """
    start_time = time.time()
    
    # Get request parameters
    technologies = request.GET.getlist('tech[]')
    search_query = request.GET.get('q', '')
    show_active = request.GET.get('show_active', 'true').lower() == 'true'
    limit = int(request.GET.get('limit', 1000))
    
    # Get viewport bounds
    viewport = {
        'north': float(request.GET.get('north', 58.7)),
        'south': float(request.GET.get('south', 50.0)),
        'east': float(request.GET.get('east', 1.8)),
        'west': float(request.GET.get('west', -8.2))
    }
    
    if not technologies:
        return JsonResponse({'error': 'No technologies specified'}, status=400)
    
    logger.info(f"Batch GeoJSON request for {len(technologies)} technologies: {technologies}")
    
    results = {}
    cache_hits = 0
    cache_misses = 0
    
    for tech in technologies:
        tech_start = time.time()
        
        # Build cache parameters
        cache_params = {
            'technology': tech,
            'query': search_query,
            'show_active': show_active,
            'limit': limit,
            **viewport
        }
        
        # Try to get from cache first
        cached_data = get_cached_map_data(cache_params)
        
        if cached_data:
            results[tech] = json.loads(cached_data)
            cache_hits += 1
            logger.info(f"Cache HIT for {tech} in {time.time() - tech_start:.3f}s")
        else:
            # Generate data for this technology
            geojson_data = generate_technology_geojson(tech, search_query, viewport, show_active, limit)
            results[tech] = geojson_data
            cache_misses += 1
            
            # Cache the result
            cache_map_data(cache_params, json.dumps(geojson_data))
            logger.info(f"Cache MISS for {tech}, generated in {time.time() - tech_start:.3f}s")
    
    total_time = time.time() - start_time
    
    # Add metadata
    metadata = {
        'total_technologies': len(technologies),
        'cache_hits': cache_hits,
        'cache_misses': cache_misses,
        'total_time': round(total_time, 3),
        'generated_at': int(time.time())
    }
    
    logger.info(f"Batch API completed: {cache_hits} hits, {cache_misses} misses in {total_time:.3f}s")
    
    return JsonResponse({
        'results': results,
        'metadata': metadata
    })


def generate_technology_geojson(technology, search_query, viewport, show_active, limit):
    """
    Generate GeoJSON data for a specific technology with optimized database queries.
    """
    # Start with base query
    location_groups = LocationGroup.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Apply viewport filtering for performance
    location_groups = location_groups.filter(
        latitude__gte=viewport['south'],
        latitude__lte=viewport['north'],
        longitude__gte=viewport['west'],
        longitude__lte=viewport['east']
    )
    
    # Apply active/inactive filter
    if show_active:
        location_groups = location_groups.filter(is_active=True)
    else:
        location_groups = location_groups.filter(is_active=False)
    
    # Apply technology filter
    if technology and technology != 'All':
        # Map technology variations
        tech_variations = get_technology_variations(technology)
        tech_filter = Q()
        for variation in tech_variations:
            tech_filter |= Q(technologies__has_key=variation)
        location_groups = location_groups.filter(tech_filter)
    
    # Apply search query if provided
    if search_query:
        if search_query.upper().startswith(('CMU', 'BMU', 'DSR')):
            location_groups = location_groups.filter(cmu_ids__contains=search_query.upper())
        else:
            search_terms = search_query.split()
            for term in search_terms:
                location_groups = location_groups.filter(
                    Q(location__icontains=term) | Q(descriptions__icontains=term)
                )
    
    # Limit results and select only needed fields
    location_groups = location_groups.only(
        'location', 'latitude', 'longitude', 'technologies', 'companies', 
        'descriptions', 'component_count', 'normalized_capacity_mw'
    )[:limit]
    
    # Build GeoJSON features
    features = []
    for loc in location_groups:
        # Get primary technology for this location
        primary_tech = get_primary_technology(loc.technologies, technology)
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(loc.longitude), float(loc.latitude)]
            },
            'properties': {
                'id': loc.id,
                'title': loc.location,
                'technology': primary_tech,
                'component_count': loc.component_count or 0,
                'capacity_mw': loc.normalized_capacity_mw or 0,
                'companies': loc.companies or {},
                'description': get_location_description(loc.descriptions)
            }
        }
        features.append(feature)
    
    return {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'count': len(features),
            'technology': technology,
            'total_capacity': sum(f['properties']['capacity_mw'] for f in features)
        }
    }


def get_technology_variations(technology):
    """Return all variations of a technology name that might exist in the database."""
    tech_variations = {
        'CHP': ['CHP', 'Combined Heat and Power (CHP)', 'CHP and autogeneration'],
        'DSR': ['DSR', 'Demand Side Response'],
        'Battery': ['Battery', 'Battery Storage', 'Battery storage'],
        'OCGT': ['Gas', 'Gas - OCGTs and reciprocating engines', 'Gas reciprocating engines', 
                'OCGT', 'Combined Cycle Gas Turbine (CCGT)'],
        'Wind': ['Wind', 'Onshore Wind', 'Offshore Wind'],
        'Solar': ['Solar', 'Solar Photovoltaics'],
        'Nuclear': ['Nuclear'],
        'Hydro': ['Hydro', 'Hydro Power', 'Pumped Storage Hydro'],
        'Biomass': ['Biomass', 'Biomass and waste'],
        'Interconnector': ['Interconnector'],
        'Coal': ['Coal']
    }
    
    return tech_variations.get(technology, [technology])


def get_primary_technology(technologies_dict, requested_tech):
    """Get the primary technology for a location, preferring the requested technology."""
    if not technologies_dict:
        return 'Unknown'
    
    # If requested technology exists, use it
    if requested_tech and requested_tech in technologies_dict:
        return requested_tech
    
    # Check for technology variations
    tech_variations = get_technology_variations(requested_tech)
    for variation in tech_variations:
        if variation in technologies_dict:
            return requested_tech  # Return the simplified name
    
    # Otherwise, return the technology with the highest count
    return max(technologies_dict.items(), key=lambda x: x[1])[0]


def get_location_description(descriptions_dict):
    """Get a concise description for the location."""
    if not descriptions_dict:
        return ''
    
    # Return the first description or the one with most occurrences
    if isinstance(descriptions_dict, dict):
        return max(descriptions_dict.items(), key=lambda x: x[1])[0]
    
    return str(descriptions_dict)


@map_access_required
@gzip_page
def optimized_geojson_stream(request):
    """
    Streaming GeoJSON endpoint for very large datasets.
    Streams data as it's generated to reduce memory usage and improve perceived performance.
    """
    technology = request.GET.get('tech', 'All')
    viewport = {
        'north': float(request.GET.get('north', 58.7)),
        'south': float(request.GET.get('south', 50.0)),
        'east': float(request.GET.get('east', 1.8)),
        'west': float(request.GET.get('west', -8.2))
    }
    
    def generate_geojson_stream():
        """Generator function that yields GeoJSON data in chunks."""
        yield '{"type":"FeatureCollection","features":['
        
        # Get query for locations
        location_groups = LocationGroup.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=viewport['south'],
            latitude__lte=viewport['north'],
            longitude__gte=viewport['west'],
            longitude__lte=viewport['east']
        ).only('location', 'latitude', 'longitude', 'technologies', 'component_count')
        
        # Apply technology filter
        if technology != 'All':
            tech_variations = get_technology_variations(technology)
            tech_filter = Q()
            for variation in tech_variations:
                tech_filter |= Q(technologies__has_key=variation)
            location_groups = location_groups.filter(tech_filter)
        
        # Stream results
        first = True
        for loc in location_groups.iterator(chunk_size=100):
            if not first:
                yield ','
            first = False
            
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(loc.longitude), float(loc.latitude)]
                },
                'properties': {
                    'id': loc.id,
                    'title': loc.location,
                    'technology': get_primary_technology(loc.technologies, technology),
                    'component_count': loc.component_count or 0
                }
            }
            yield json.dumps(feature)
        
        yield '],"metadata":{"streaming":true}}'
    
    return StreamingHttpResponse(
        generate_geojson_stream(),
        content_type='application/json'
    )