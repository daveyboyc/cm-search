"""
Optimize map API to use direct database queries with minimal overhead
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.db import connection
from django.core.cache import cache
import json

def get_optimized_map_data(technology=None, bounds=None):
    """
    Get map data with raw SQL for maximum performance
    """
    
    # Build query with filters
    where_clauses = ["geocoded = true"]
    params = []
    
    if technology:
        where_clauses.append("technology ILIKE %s")
        params.append(f"%{technology}%")
    
    if bounds:
        where_clauses.append("""
            latitude BETWEEN %s AND %s 
            AND longitude BETWEEN %s AND %s
        """)
        params.extend([bounds['south'], bounds['north'], 
                      bounds['west'], bounds['east']])
    
    # Only get essential fields
    query = f"""
        SELECT 
            id, location, latitude, longitude, 
            technology, company_name, delivery_year
        FROM checker_component
        WHERE {' AND '.join(where_clauses)}
        ORDER BY delivery_year DESC
        LIMIT 1000
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

def create_cluster_data(components, zoom_level):
    """
    Simple clustering algorithm for map markers
    """
    if zoom_level < 8:
        # Group by rounded coordinates
        clusters = {}
        grid_size = 0.1 if zoom_level >= 6 else 0.5
        
        for comp in components:
            lat = round(comp['latitude'] / grid_size) * grid_size
            lng = round(comp['longitude'] / grid_size) * grid_size
            key = f"{lat},{lng}"
            
            if key not in clusters:
                clusters[key] = {
                    'lat': lat,
                    'lng': lng,
                    'count': 0,
                    'ids': []
                }
            
            clusters[key]['count'] += 1
            clusters[key]['ids'].append(comp['id'])
        
        return list(clusters.values())
    else:
        # Return individual markers at high zoom
        return [{
            'lat': comp['latitude'],
            'lng': comp['longitude'],
            'count': 1,
            'ids': [comp['id']]
        } for comp in components]

# Example usage
if __name__ == '__main__':
    # Test optimized query
    import time
    
    start = time.time()
    data = get_optimized_map_data(technology='Battery')
    print(f"Loaded {len(data)} components in {time.time() - start:.3f}s")
    
    start = time.time()
    clusters = create_cluster_data(data, zoom_level=6)
    print(f"Created {len(clusters)} clusters in {time.time() - start:.3f}s")