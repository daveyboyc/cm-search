#!/usr/bin/env python
"""
Create static JSON files for map data to reduce database/Redis load
"""
import os
import sys
import django
import json
from collections import defaultdict

# Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count

def create_static_map_cache():
    """Create static JSON files for map data"""
    
    # Create directory for static cache
    cache_dir = 'checker/static/cache'
    os.makedirs(cache_dir, exist_ok=True)
    
    print("Creating static cache files...")
    
    # 1. Technology summaries
    tech_summary = {}
    technologies = Component.objects.values('technology').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for tech in technologies:
        if tech['technology']:
            tech_summary[tech['technology']] = tech['count']
    
    with open(f'{cache_dir}/technology_summary.json', 'w') as f:
        json.dump(tech_summary, f)
    print(f"✓ Created technology summary: {len(tech_summary)} technologies")
    
    # 2. Company summaries (Top 100)
    company_summary = {}
    companies = Component.objects.exclude(
        company_name__in=["AXLE ENERGY LIMITED", "OCTOPUS ENERGY LIMITED"]
    ).values('company_name').annotate(
        count=Count('id')
    ).order_by('-count')[:100]
    
    for company in companies:
        if company['company_name']:
            company_summary[company['company_name']] = company['count']
    
    with open(f'{cache_dir}/company_summary.json', 'w') as f:
        json.dump(company_summary, f)
    print(f"✓ Created company summary: {len(company_summary)} companies")
    
    # 3. Location index (for search)
    location_index = defaultdict(list)
    components = Component.objects.filter(
        geocoded=True
    ).values('location', 'latitude', 'longitude', 'technology', 'delivery_year')
    
    for comp in components:
        if comp['location']:
            location_index[comp['location'][:3].upper()].append({
                'loc': comp['location'],
                'lat': float(comp['latitude']) if comp['latitude'] else None,
                'lng': float(comp['longitude']) if comp['longitude'] else None,
                'tech': comp['technology'],
                'year': comp['delivery_year']
            })
    
    # Save location index by first 3 letters
    for prefix, locations in location_index.items():
        # Clean prefix to be filesystem safe
        safe_prefix = prefix.replace('/', '_').replace(' ', '_')
        if safe_prefix:
            with open(f'{cache_dir}/loc_{safe_prefix}.json', 'w') as f:
                json.dump(locations, f)
    
    print(f"✓ Created location indexes: {len(location_index)} prefixes")
    
    # 4. Basic map markers by technology (limit to recent years)
    for tech_name in ['Gas', 'Battery', 'DSR', 'Wind', 'Solar']:
        markers = []
        components = Component.objects.filter(
            technology__icontains=tech_name,
            geocoded=True,
            delivery_year__gte='2020'  # Only recent components
        ).values('id', 'location', 'latitude', 'longitude', 'company_name', 'delivery_year')[:500]
        
        for comp in components:
            markers.append({
                'id': comp['id'],
                'loc': comp['location'],
                'lat': float(comp['latitude']) if comp['latitude'] else None,
                'lng': float(comp['longitude']) if comp['longitude'] else None,
                'company': comp['company_name'],
                'year': comp['delivery_year']
            })
        
        with open(f'{cache_dir}/markers_{tech_name.lower()}.json', 'w') as f:
            json.dump(markers, f)
        
        print(f"✓ Created {tech_name} markers: {len(markers)} components")

if __name__ == '__main__':
    create_static_map_cache()
    print("\nStatic cache created successfully!")