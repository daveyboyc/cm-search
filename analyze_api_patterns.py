# Python script to analyze your API patterns locally

import re
from collections import defaultdict

# Common API endpoints that might cause high egress
api_patterns = {
    '/api/map-data/': 'Map data requests (potentially large GeoJSON)',
    '/api/search-geojson/': 'Search results as GeoJSON',
    '/api/component-map-detail/': 'Individual component details',
    '/rest/v1/checker_component': 'Direct component table access',
    '/rest/v1/checker_locationgroup': 'Location group access',
}

# Estimate data sizes
estimates = {
    'checker_component': {
        'avg_row_size': 500,  # bytes
        'typical_query_rows': 1000,
        'problem': 'Each map zoom/pan might fetch 1000+ components'
    },
    'checker_locationgroup': {
        'avg_row_size': 300,
        'typical_query_rows': 500,
        'problem': 'Location searches return many groups'
    }
}

print("Potential Egress Culprits:")
print("-" * 50)

for endpoint, description in api_patterns.items():
    print(f"\n{endpoint}")
    print(f"  Description: {description}")
    
    if 'component' in endpoint:
        est = estimates['checker_component']
        data_per_request = (est['avg_row_size'] * est['typical_query_rows']) / 1024 / 1024
        print(f"  Est. data per request: {data_per_request:.2f} MB")
        print(f"  Problem: {est['problem']}")
        print(f"  If called 1000x/day: {data_per_request * 1000:.2f} MB/day")
