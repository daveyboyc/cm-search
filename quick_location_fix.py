#!/usr/bin/env python
"""Quick fix for location search - generate minimal static mapping"""
import os
import json
import django
import sys
from collections import defaultdict
import time

# Add the project directory to the Python path  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count

def quick_location_fix():
    """Generate minimal location mapping to fix 5.6s delays"""
    
    print("🚨 EMERGENCY FIX: Creating static location mappings")
    print("=" * 50)
    
    start = time.time()
    
    # Create output directory
    os.makedirs('static/cache', exist_ok=True)
    
    # 1. Build outward code to locations mapping (PRIMARY FIX)
    print("\n📍 Building outward code mappings (this fixes SW11 searches)...")
    outward_mapping = defaultdict(list)
    
    # Query for unique outward code + location combinations
    results = Component.objects.values('outward_code', 'location').distinct()
    
    for r in results:
        if r['outward_code'] and r['location']:
            outward_mapping[r['outward_code'].upper()].append(r['location'])
    
    # Save as JSON
    with open('static/cache/outward_locations.json', 'w') as f:
        json.dump(dict(outward_mapping), f, separators=(',', ':'))
    
    print(f"✅ Generated {len(outward_mapping)} outward code mappings")
    
    # 2. Build location counts (for sorting results)
    print("\n📊 Building location counts...")
    location_counts = {}
    
    counts = Component.objects.values('location').annotate(
        count=Count('id')
    ).filter(location__isnull=False)
    
    for c in counts:
        location_counts[c['location']] = c['count']
    
    with open('static/cache/location_counts.json', 'w') as f:
        json.dump(location_counts, f, separators=(',', ':'))
    
    print(f"✅ Generated counts for {len(location_counts)} locations")
    
    # 3. Create a simple search index
    print("\n🔍 Building search index...")
    search_index = defaultdict(set)
    
    # Index location names by first 3 chars
    for loc in location_counts.keys():
        if len(loc) >= 3:
            key = loc[:3].upper()
            search_index[key].add(loc)
    
    # Convert sets to lists and save
    search_dict = {k: list(v) for k, v in search_index.items()}
    
    with open('static/cache/search_index.json', 'w') as f:
        json.dump(search_dict, f, separators=(',', ':'))
    
    print(f"✅ Generated {len(search_dict)} search prefixes")
    
    elapsed = time.time() - start
    print(f"\n✅ Complete in {elapsed:.2f} seconds!")
    print("\n📁 Files created:")
    print("  - static/cache/outward_locations.json")
    print("  - static/cache/location_counts.json") 
    print("  - static/cache/search_index.json")
    
    # Calculate total size
    total_size = 0
    for fname in ['outward_locations.json', 'location_counts.json', 'search_index.json']:
        fpath = f'static/cache/{fname}'
        if os.path.exists(fpath):
            total_size += os.path.getsize(fpath)
    
    print(f"\n💾 Total size: {total_size / 1024:.1f} KB")
    print("\n🚀 Next steps:")
    print("1. Deploy these files to GitHub Pages or CDN")
    print("2. Update location_search.py to use static files")
    print("3. This will reduce location search from 5.6s to <10ms!")

if __name__ == '__main__':
    quick_location_fix()