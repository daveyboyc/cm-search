"""
Optimized Search GeoJSON API endpoint with reduced egress
"""
from django.http import JsonResponse
from django.db.models import Q
from checker.models import LocationGroup
import time

# Monitoring import
try:
    from monitoring.decorators import monitor_api
except ImportError:
    def monitor_api(func):
        return func

@monitor_api
def search_results_geojson_minimal(request):
    """
    Return search results as MINIMAL GeoJSON for map display.
    Reduces egress by only sending essential data for map markers.
    """
    start_time = time.time()
    
    # Get parameters
    search_query = request.GET.get('q', '')
    tech_filter = request.GET.get('tech', '')
    company_filter = request.GET.get('company', '')  # Add company filtering for map-explorer
    show_active = request.GET.get('show_active', 'true').lower() == 'true'
    
    # REDUCED LIMIT for less egress
    limit = int(request.GET.get('limit', 500))  # Reduced from 1000
    
    # Minimal mode flag
    minimal = request.GET.get('minimal', 'true').lower() == 'true'
    
    if not search_query and not tech_filter and not company_filter:
        return JsonResponse({
            'type': 'FeatureCollection',
            'features': [],
            'metadata': {'count': 0, 'total': 0}
        })
    
    # Query LocationGroups
    location_groups = LocationGroup.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Apply filters
    if show_active:
        location_groups = location_groups.filter(is_active=True)
    else:
        location_groups = location_groups.filter(is_active=False)
    
    # Handle search
    if search_query:
        if search_query.upper().startswith(('CMU', 'BMU', 'DSR')):
            location_groups = location_groups.filter(cmu_ids__contains=search_query.upper())
        else:
            search_terms = search_query.split()
            for term in search_terms:
                location_groups = location_groups.filter(location__icontains=term)
    
    # Handle technology filter
    if tech_filter and tech_filter != 'All':
        location_groups = location_groups.filter(technologies__has_key=tech_filter)
    
    # Handle company filter - ESSENTIAL for map-explorer company selection
    if company_filter and company_filter != 'All':
        location_groups = location_groups.filter(companies__has_key=company_filter)
    
    # Get count and apply limit
    total_count = location_groups.count()
    
    if total_count > limit:
        return JsonResponse({
            'type': 'FeatureCollection',
            'features': [],
            'metadata': {
                'count': 0,
                'total': total_count,
                'error': True,
                'error_message': f'Too many results ({total_count}). Please refine your search.'
            }
        })
    
    # Fetch data with optimized query
    location_groups = location_groups.only(
        'id', 'location', 'latitude', 'longitude', 
        'technologies', 'component_count', 'normalized_capacity_mw'
    )[:limit]
    
    # Convert to MINIMAL GeoJSON
    features = []
    
    for lg in location_groups:
        # Get dominant technology only
        technologies = lg.technologies or {}
        dominant_tech = max(technologies.items(), key=lambda x: x[1])[0] if technologies else 'Unknown'
        
        if minimal:
            # MINIMAL data for map display only
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lg.longitude, lg.latitude]
                },
                'properties': {
                    'id': lg.id,
                    'title': lg.location,
                    'technology': dominant_tech,
                    'count': lg.component_count,
                    'capacity': round(lg.normalized_capacity_mw, 2)
                }
            }
        else:
            # Include more data only if requested
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lg.longitude, lg.latitude]
                },
                'properties': {
                    'id': lg.id,
                    'title': lg.location,
                    'technology': dominant_tech,
                    'all_technologies': technologies,
                    'component_count': lg.component_count,
                    'capacity_mw': lg.normalized_capacity_mw,
                    'detailUrl': f'/location/{lg.id}/'
                }
            }
        
        features.append(feature)
    
    # Return optimized response
    response_data = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'count': len(features),
            'total': total_count,
            'processing_time': f"{(time.time() - start_time):.3f}s",
            'minimal': minimal
        }
    }
    
    return JsonResponse(response_data)