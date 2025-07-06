#!/usr/bin/env python3
"""
Test to confirm map queries are the main egress culprit
"""
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup, Component

def test_map_query_size():
    """Test how much data map queries actually transfer"""
    print("🗺️  MAP QUERY EGRESS ANALYSIS")
    print("=" * 50)
    
    # Test 1: Typical UK viewport query
    print("\n1. Testing UK viewport query (what map loads):")
    uk_bounds = {
        'north': 55.0,
        'south': 50.0,
        'east': 1.8,
        'west': -5.7
    }
    
    # Simulate what the map does
    components = Component.objects.filter(
        geocoded=True,
        latitude__gte=uk_bounds['south'],
        latitude__lte=uk_bounds['north'],
        longitude__gte=uk_bounds['west'],
        longitude__lte=uk_bounds['east']
    )
    
    count = components.count()
    print(f"   Components in viewport: {count}")
    
    # Calculate data size
    if count > 0:
        # Get first 100 to estimate size
        sample = list(components[:100])
        avg_size = sum(len(str(c.__dict__)) for c in sample) / len(sample)
        total_size_mb = (avg_size * count) / (1024 * 1024)
        print(f"   Estimated data size: {total_size_mb:.1f} MB")
    
    # Test 2: LocationGroup query
    print("\n2. Testing LocationGroup query:")
    location_groups = LocationGroup.objects.filter(
        latitude__gte=uk_bounds['south'],
        latitude__lte=uk_bounds['north'],
        longitude__gte=uk_bounds['west'],
        longitude__lte=uk_bounds['east']
    )
    
    lg_count = location_groups.count()
    print(f"   LocationGroups in viewport: {lg_count}")
    
    if lg_count > 0:
        # Sample size calculation
        sample_lg = list(location_groups[:100])
        avg_lg_size = sum(len(str(lg.__dict__)) for lg in sample_lg) / len(sample_lg)
        total_lg_size_mb = (avg_lg_size * lg_count) / (1024 * 1024)
        print(f"   Estimated data size: {total_lg_size_mb:.1f} MB")
    
    # Test 3: API endpoint test
    print("\n3. Testing actual map API response size:")
    try:
        response = requests.get(
            "http://localhost:8000/api/map-data/",
            params={
                'north': 55.0,
                'south': 50.0,
                'east': 1.8,
                'west': -5.7
            },
            timeout=10
        )
        
        size_kb = len(response.content) / 1024
        print(f"   API response size: {size_kb:.1f} KB")
        
        # Parse response to see feature count
        try:
            data = response.json()
            if 'features' in data:
                print(f"   Features returned: {len(data['features'])}")
        except:
            pass
            
    except Exception as e:
        print(f"   API test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 CONCLUSION:")
    print("If map queries transfer >100KB per request and run")
    print("6,313 times per day, that's 600MB+ from maps alone!")

if __name__ == "__main__":
    test_map_query_size()