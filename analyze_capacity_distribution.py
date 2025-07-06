#!/usr/bin/env python
"""
Analyze capacity field distribution and aggregation issues
"""
import os
import sys
import django
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count, Sum, Q
import re

def analyze_capacity_field_coverage():
    """Check which capacity fields are available across ALL components"""
    print("\nCAPACITY FIELD COVERAGE ANALYSIS")
    print("=" * 80)
    
    total = Component.objects.count()
    
    # Track different capacity sources
    capacity_coverage = {
        'derated_capacity_mw': 0,
        'de_rated_additional': 0,
        'connection_dsr': 0,
        'anticipated': 0,
        'any_capacity': 0,
        'no_capacity': 0
    }
    
    # Sample all components in batches
    batch_size = 1000
    for offset in range(0, min(total, 20000), batch_size):  # Analyze first 20k
        components = Component.objects.all()[offset:offset+batch_size]
        
        for comp in components:
            has_any_capacity = False
            
            # Check main field
            if comp.derated_capacity_mw is not None:
                capacity_coverage['derated_capacity_mw'] += 1
                has_any_capacity = True
            
            # Check additional_data fields
            if comp.additional_data:
                if comp.additional_data.get('De-Rated Capacity') not in [None, 'None', 'N/A', '-', '']:
                    capacity_coverage['de_rated_additional'] += 1
                    has_any_capacity = True
                
                if comp.additional_data.get('Connection / DSR Capacity') not in [None, 'None', 'N/A', '-', '']:
                    capacity_coverage['connection_dsr'] += 1
                    has_any_capacity = True
                
                if comp.additional_data.get('Anticipated De-Rated Capacity') not in [None, 'None', 'N/A', '-', '']:
                    capacity_coverage['anticipated'] += 1
                    has_any_capacity = True
            
            if has_any_capacity:
                capacity_coverage['any_capacity'] += 1
            else:
                capacity_coverage['no_capacity'] += 1
    
    analyzed = min(total, 20000)
    print(f"\nAnalyzed {analyzed:,} components:")
    for field, count in capacity_coverage.items():
        pct = (count / analyzed) * 100
        print(f"  {field}: {count:,} ({pct:.1f}%)")
    
    return capacity_coverage

def find_aggregated_cmus():
    """Find CMUs that appear to be aggregated across multiple locations"""
    print("\n\nAGGREGATED CMU ANALYSIS")
    print("=" * 80)
    
    # Find CMUs with multiple locations
    cmu_locations = defaultdict(set)
    cmu_capacities = defaultdict(list)
    cmu_companies = defaultdict(set)
    
    components = Component.objects.exclude(
        Q(cmu_id__isnull=True) | Q(cmu_id='')
    ).values('cmu_id', 'location', 'derated_capacity_mw', 'company_name')[:10000]
    
    for comp in components:
        cmu_id = comp['cmu_id']
        location = comp['location']
        
        if location and location not in ['None', 'N/A', 'TBC']:
            cmu_locations[cmu_id].add(location)
            if comp['derated_capacity_mw']:
                cmu_capacities[cmu_id].append(comp['derated_capacity_mw'])
            if comp['company_name']:
                cmu_companies[cmu_id].add(comp['company_name'])
    
    # Find CMUs with multiple locations
    multi_location_cmus = [(cmu, len(locs)) for cmu, locs in cmu_locations.items() if len(locs) > 1]
    multi_location_cmus.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nTop 10 CMUs with multiple locations (likely aggregated):")
    for cmu_id, loc_count in multi_location_cmus[:10]:
        locations = list(cmu_locations[cmu_id])[:3]
        companies = list(cmu_companies[cmu_id])
        capacities = cmu_capacities[cmu_id]
        
        print(f"\nCMU: {cmu_id}")
        print(f"  Locations: {loc_count}")
        print(f"  Companies: {', '.join(companies[:2])}")
        print(f"  Sample locations: {', '.join(locations)}")
        if capacities:
            print(f"  Capacity values: {set(capacities)} MW")
            if len(set(capacities)) == 1:
                print(f"  ⚠️  All locations show same capacity: {capacities[0]} MW (likely aggregated)")

def analyze_flexitricity_asda():
    """Specific analysis of Flexitricity ASDA aggregation issue"""
    print("\n\nFLEXITRICITY ASDA ANALYSIS")
    print("=" * 80)
    
    # Find ASDA components
    asda_components = Component.objects.filter(
        Q(location__icontains='asda') | 
        Q(company_name__icontains='flexitricity')
    ).values('location', 'company_name', 'cmu_id', 'derated_capacity_mw', 'description')
    
    # Group by CMU
    asda_by_cmu = defaultdict(list)
    for comp in asda_components:
        if 'asda' in (comp['location'] or '').lower():
            asda_by_cmu[comp['cmu_id']].append(comp)
    
    print(f"\nFound {len(asda_by_cmu)} CMUs with ASDA locations")
    
    for cmu_id, components in list(asda_by_cmu.items())[:5]:
        print(f"\nCMU: {cmu_id}")
        print(f"  Number of ASDA locations: {len(components)}")
        
        # Get unique capacities
        capacities = [c['derated_capacity_mw'] for c in components if c['derated_capacity_mw']]
        if capacities:
            unique_capacities = set(capacities)
            print(f"  Capacity values: {unique_capacities}")
            
            if len(unique_capacities) == 1:
                total_capacity = list(unique_capacities)[0]
                capacity_per_location = total_capacity / len(components)
                print(f"  ⚠️  All show {total_capacity} MW - likely aggregated")
                print(f"  📊 Actual capacity per location: {capacity_per_location:.2f} MW")
        
        # Show sample locations
        for comp in components[:3]:
            print(f"    - {comp['location'][:50]}...")

def propose_capacity_normalization():
    """Propose solution for capacity normalization"""
    print("\n\nCAPACITY NORMALIZATION PROPOSAL")
    print("=" * 80)
    
    print("\nProblem Summary:")
    print("1. Some CMUs aggregate capacity across multiple locations")
    print("2. Each location shows total CMU capacity, not its share")
    print("3. This inflates capacity for sorting and calculations")
    
    print("\nProposed Solution:")
    print("\n1. Add fields to LocationGroup model:")
    print("   - aggregated_cmu: Boolean")
    print("   - location_count_in_cmu: Integer") 
    print("   - normalized_capacity_mw: Float")
    print("   - capacity_calculation_method: String")
    
    print("\n2. Detection algorithm:")
    print("   IF same CMU_ID appears at multiple locations")
    print("   AND all locations show identical capacity")
    print("   THEN mark as aggregated")
    print("   AND normalized_capacity = total_capacity / location_count")
    
    print("\n3. Capacity calculation priority:")
    print("   a. If single location CMU: use stated capacity")
    print("   b. If aggregated CMU: use normalized capacity")
    print("   c. If mixed (different capacities): use location-specific value")
    
    print("\n4. Display both values:")
    print("   'This location: 0.1 MW (part of 10 MW aggregated CMU)'")

def test_capacity_sorting_impact():
    """Show how different capacity methods affect sorting"""
    print("\n\nCAPACITY SORTING IMPACT TEST")
    print("=" * 80)
    
    # Get sample of components with different capacity sources
    test_components = []
    
    # Components with only derated
    with_derated = Component.objects.filter(
        derated_capacity_mw__isnull=False
    ).exclude(location__in=['None', 'N/A'])[:5]
    
    for comp in with_derated:
        test_components.append({
            'location': comp.location[:50],
            'derated': comp.derated_capacity_mw,
            'connection': comp.additional_data.get('Connection / DSR Capacity') if comp.additional_data else None,
            'source': 'derated_only'
        })
    
    # Components with only connection capacity
    with_connection = Component.objects.filter(
        derated_capacity_mw__isnull=True
    ).exclude(location__in=['None', 'N/A'])[:10]
    
    connection_found = 0
    for comp in with_connection:
        if comp.additional_data and comp.additional_data.get('Connection / DSR Capacity'):
            try:
                conn_value = float(comp.additional_data.get('Connection / DSR Capacity'))
                test_components.append({
                    'location': comp.location[:50],
                    'derated': None,
                    'connection': conn_value,
                    'source': 'connection_only'
                })
                connection_found += 1
                if connection_found >= 5:
                    break
            except:
                pass
    
    print("\nExample of sorting bias:")
    print("\nUsing any available capacity:")
    test_components.sort(key=lambda x: x['connection'] or x['derated'] or 0, reverse=True)
    for i, comp in enumerate(test_components[:10]):
        capacity = comp['connection'] or comp['derated'] or 0
        print(f"{i+1}. {comp['location']}: {capacity:.2f} MW ({comp['source']})")
    
    print("\nUsing only derated capacity:")
    test_components.sort(key=lambda x: x['derated'] or 0, reverse=True)
    for i, comp in enumerate(test_components[:10]):
        capacity = comp['derated'] or 0
        print(f"{i+1}. {comp['location']}: {capacity:.2f} MW ({comp['source']})")

if __name__ == "__main__":
    # Run all analyses
    analyze_capacity_field_coverage()
    find_aggregated_cmus()
    analyze_flexitricity_asda()
    propose_capacity_normalization()
    test_capacity_sorting_impact()