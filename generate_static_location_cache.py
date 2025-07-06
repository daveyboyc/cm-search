#!/usr/bin/env python
"""Generate static location mapping files to eliminate 5.6s location searches"""
import os
import json
import django
import sys
from collections import defaultdict

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count, Q
import time

def generate_location_mappings():
    """Generate static JSON files for location lookups"""
    
    print("🚀 Generating static location cache to fix 5.6s lookup times")
    print("=" * 60)
    
    start_time = time.time()
    
    # Create output directory
    output_dir = 'static_cache/locations'
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Generate postcode to location mapping
    print("\n📍 Building postcode mappings...")
    postcode_mapping = defaultdict(set)
    
    # Get all components with outward codes (e.g., SW11)
    components = Component.objects.exclude(
        Q(outward_code__isnull=True) | Q(outward_code='')
    ).values('location', 'outward_code').distinct()
    
    for comp in components:
        # Outward code mapping (e.g., SW11)
        if comp['outward_code'] and comp['location']:
            postcode_mapping[comp['outward_code'].upper()].add(comp['location'])
    
    # Convert sets to lists for JSON serialization
    postcode_dict = {k: list(v) for k, v in postcode_mapping.items()}
    
    # Save postcode mappings
    with open(f'{output_dir}/postcode_to_locations.json', 'w') as f:
        json.dump(postcode_dict, f, separators=(',', ':'))
    
    print(f"✅ Generated {len(postcode_dict)} postcode mappings")
    
    # 2. Generate location to components mapping
    print("\n📍 Building location to components mapping...")
    location_components = defaultdict(list)
    
    # Get component counts by location
    location_stats = Component.objects.values('location').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for stat in location_stats:
        location = stat['location']
        if location:
            # Get basic info for each component at this location
            components = Component.objects.filter(location=location).values(
                'id', 'cmu_id', 'technology', 'derated_capacity_mw',
                'latitude', 'longitude', 'outward_code'
            )[:100]  # Limit to top 100 components per location
            
            location_components[location] = {
                'count': stat['count'],
                'components': list(components)
            }
    
    # Save location mappings
    with open(f'{output_dir}/location_to_components.json', 'w') as f:
        json.dump(location_components, f, separators=(',', ':'))
    
    print(f"✅ Generated mappings for {len(location_components)} locations")
    
    # 3. Generate common search terms mapping
    print("\n🔍 Building search term mappings...")
    search_terms = defaultdict(set)
    
    # Map common terms to locations
    for location in Component.objects.values_list('location', flat=True).distinct():
        if location:
            # Split location into searchable terms
            terms = location.lower().split()
            for term in terms:
                if len(term) >= 3:  # Only index terms 3+ chars
                    search_terms[term].add(location)
    
    # Convert and save
    search_dict = {k: list(v) for k, v in search_terms.items() if len(v) < 100}  # Limit to reasonable size
    
    with open(f'{output_dir}/search_terms.json', 'w') as f:
        json.dump(search_dict, f, separators=(',', ':'))
    
    print(f"✅ Generated {len(search_dict)} search term mappings")
    
    # 4. Generate location coordinates for map centering
    print("\n🗺️  Building location coordinates...")
    location_coords = {}
    
    # Get locations with valid coordinates
    coords = Component.objects.exclude(
        Q(latitude__isnull=True) | Q(longitude__isnull=True)
    ).values('location', 'latitude', 'longitude').distinct()
    
    for coord in coords:
        if coord['location'] and coord['latitude'] and coord['longitude']:
            location_coords[coord['location']] = {
                'lat': float(coord['latitude']),
                'lng': float(coord['longitude'])
            }
    
    with open(f'{output_dir}/location_coordinates.json', 'w') as f:
        json.dump(location_coords, f, separators=(',', ':'))
    
    print(f"✅ Generated coordinates for {len(location_coords)} locations")
    
    # Generate index file
    index = {
        'generated': time.strftime('%Y-%m-%d %H:%M:%S'),
        'files': {
            'postcode_to_locations': 'postcode_to_locations.json',
            'location_to_components': 'location_to_components.json',
            'search_terms': 'search_terms.json',
            'location_coordinates': 'location_coordinates.json'
        },
        'stats': {
            'postcodes': len(postcode_dict),
            'locations': len(location_components),
            'search_terms': len(search_dict),
            'coordinates': len(location_coords)
        }
    }
    
    with open(f'{output_dir}/index.json', 'w') as f:
        json.dump(index, f, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n✅ Static cache generation complete in {elapsed:.2f} seconds")
    print(f"📁 Files saved to: {output_dir}/")
    
    # Calculate size savings
    total_size = 0
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        total_size += os.path.getsize(filepath)
    
    print(f"💾 Total cache size: {total_size / 1024 / 1024:.2f} MB")
    print("\n🚀 These files can be served from GitHub Pages or any CDN!")

if __name__ == '__main__':
    generate_location_mappings()