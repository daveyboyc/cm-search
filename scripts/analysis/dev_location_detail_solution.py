#!/usr/bin/env python
"""
Test solution for location detail pages with capacity handling and raw data access
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component, CMURegistry
from django.db.models import Count, Sum, Avg, Q
from collections import defaultdict

def get_capacity_value(component):
    """
    Get the best available capacity value for a component.
    Priority order based on analysis:
    1. derated_capacity_mw (if available)
    2. additional_data['De-Rated Capacity'] 
    3. additional_data['Connection / DSR Capacity']
    4. CMU Registry data (if available)
    """
    # 1. Check derated_capacity_mw first (most reliable)
    if component.derated_capacity_mw is not None:
        return component.derated_capacity_mw, 'derated_capacity_mw'
    
    # 2. Check additional_data
    if component.additional_data:
        # Try De-Rated Capacity
        derated = component.additional_data.get('De-Rated Capacity')
        if derated and str(derated).lower() not in ['none', 'n/a', '-', '']:
            try:
                return float(derated), 'additional_data[De-Rated Capacity]'
            except (ValueError, TypeError):
                pass
        
        # Try Connection / DSR Capacity
        connection = component.additional_data.get('Connection / DSR Capacity')
        if connection and str(connection).lower() not in ['none', 'n/a', '-', '']:
            try:
                return float(connection), 'additional_data[Connection / DSR Capacity]'
            except (ValueError, TypeError):
                pass
    
    return None, None

def calculate_location_capacity(location_name):
    """
    Calculate capacity for a location using the best available method
    """
    components = Component.objects.filter(location=location_name)
    
    # Group by description (asset)
    assets = defaultdict(lambda: {
        'components': [],
        'capacities': [],
        'capacity_sources': []
    })
    
    for comp in components:
        desc = comp.description or 'No Description'
        capacity, source = get_capacity_value(comp)
        
        assets[desc]['components'].append(comp)
        if capacity is not None:
            assets[desc]['capacities'].append(capacity)
            assets[desc]['capacity_sources'].append(source)
    
    # Calculate capacity for each asset
    location_capacity = 0
    asset_summaries = []
    
    for desc, data in assets.items():
        if data['capacities']:
            # Use the most common capacity value (mode) for this asset
            from statistics import mode, StatisticsError
            try:
                asset_capacity = mode(data['capacities'])
            except StatisticsError:
                # If no mode, use average
                asset_capacity = sum(data['capacities']) / len(data['capacities'])
            
            location_capacity += asset_capacity
            
            asset_summaries.append({
                'description': desc,
                'capacity': asset_capacity,
                'confidence': 'high' if len(set(data['capacities'])) == 1 else 'medium',
                'data_points': len(data['capacities']),
                'total_records': len(data['components']),
                'sources': list(set(data['capacity_sources']))
            })
        else:
            asset_summaries.append({
                'description': desc,
                'capacity': None,
                'confidence': 'none',
                'data_points': 0,
                'total_records': len(data['components']),
                'sources': []
            })
    
    return {
        'total_capacity': location_capacity,
        'assets': asset_summaries,
        'calculation_method': 'sum_of_unique_assets'
    }

def design_raw_data_access():
    """
    Design how to handle raw data access for 25+ components on demand
    """
    print("\nRAW DATA ACCESS DESIGN")
    print("=" * 80)
    
    print("\nProposed Solution:")
    print("1. Location detail page shows summary data only")
    print("2. Add 'View Raw Data' buttons that load on demand via AJAX")
    print("3. Options for raw data access:")
    print("   a) Individual component raw data (click to expand)")
    print("   b) Bulk download all raw data as JSON/CSV")
    print("   c) API endpoint: /api/location/{id}/raw-data/")
    
    print("\nExample API endpoints:")
    print("   GET /api/component/{id}/raw-data/")
    print("   GET /api/location/{location_id}/components/raw-data/")
    print("   GET /api/cmu/{cmu_id}/registry-data/")
    
    print("\nBenefits:")
    print("   - Fast initial page load")
    print("   - Raw data available when needed")
    print("   - Reduces server memory usage")
    print("   - Can cache raw data separately")

def test_imperial_college_capacity():
    """Test capacity calculation for Imperial College"""
    print("\nIMPERIAL COLLEGE CAPACITY CALCULATION TEST")
    print("=" * 80)
    
    result = calculate_location_capacity("Imperial College London")
    
    print(f"Total calculated capacity: {result['total_capacity']:.2f} MW")
    print(f"Calculation method: {result['calculation_method']}")
    
    print("\nAsset breakdown:")
    for asset in result['assets']:
        print(f"\n{asset['description'][:60]}...")
        if asset['capacity']:
            print(f"  Capacity: {asset['capacity']:.2f} MW")
            print(f"  Confidence: {asset['confidence']}")
            print(f"  Data points: {asset['data_points']}/{asset['total_records']}")
            print(f"  Sources: {', '.join(asset['sources'])}")
        else:
            print(f"  Capacity: No data available")
            print(f"  Records: {asset['total_records']}")

def test_complex_location():
    """Test a location with many components"""
    print("\n\nCOMPLEX LOCATION TEST")
    print("=" * 80)
    
    # Find a location with many components
    top_location = Component.objects.exclude(
        location__in=['None', 'N/A', 'NA', 'TBC']
    ).values('location').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    if top_location:
        location = top_location['location']
        count = top_location['count']
        
        print(f"Testing: {location}")
        print(f"Component count: {count}")
        
        result = calculate_location_capacity(location)
        
        print(f"\nCalculated total capacity: {result['total_capacity']:.2f} MW")
        print(f"Number of unique assets: {len(result['assets'])}")
        
        # Show summary
        with_capacity = sum(1 for a in result['assets'] if a['capacity'])
        print(f"Assets with capacity data: {with_capacity}/{len(result['assets'])}")

if __name__ == "__main__":
    # Run capacity value analysis
    print("CAPACITY VALUE ANALYSIS")
    print("=" * 80)
    print("\nKey findings from analysis:")
    print("1. Only 7.7% of components have derated_capacity_mw in main field")
    print("2. ~21% have capacity data in additional_data['De-Rated Capacity']")
    print("3. ~21% have capacity data in additional_data['Connection / DSR Capacity']")
    print("4. Imperial College has both types - can use for validation")
    
    # Test capacity calculation
    test_imperial_college_capacity()
    test_complex_location()
    
    # Show raw data solution
    design_raw_data_access()