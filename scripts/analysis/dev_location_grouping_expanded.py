#!/usr/bin/env python
import os
import sys
import django
from collections import defaultdict
import json

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count, Sum, Q, Min, Max

def analyze_battery_components():
    """Analyze battery components specifically"""
    print("\n" + "="*80)
    print("BATTERY COMPONENTS ANALYSIS")
    print("="*80)
    
    battery_components = Component.objects.filter(
        Q(description__icontains='battery') | 
        Q(technology__icontains='battery')
    )
    
    total = battery_components.count()
    print(f"Total battery components: {total}")
    
    # Group by location
    locations = battery_components.values('location').annotate(
        count=Count('id'),
        total_capacity=Sum('derated_capacity_mw'),
        unique_descriptions=Count('description', distinct=True),
        unique_cmus=Count('cmu_id', distinct=True)
    ).order_by('-count')
    
    print(f"Unique battery locations: {len(locations)}")
    print(f"\nTop 10 battery locations by component count:")
    
    for i, loc in enumerate(locations[:10]):
        print(f"\n{i+1}. {loc['location']}")
        print(f"   Components: {loc['count']}")
        print(f"   Unique descriptions: {loc['unique_descriptions']}")
        print(f"   Unique CMUs: {loc['unique_cmus']}")
        print(f"   Total capacity: {loc['total_capacity']:.2f} MW" if loc['total_capacity'] else "   Total capacity: Unknown")

def analyze_all_components_grouped():
    """Analyze ALL components with proper grouping"""
    print("\n" + "="*80)
    print("FULL DATABASE GROUPING ANALYSIS")
    print("="*80)
    
    # Exclude invalid locations
    valid_components = Component.objects.exclude(
        Q(location__isnull=True) |
        Q(location='') |
        Q(location='None') |
        Q(location='N/A') |
        Q(location='NA') |
        Q(location__icontains='TBC') |
        Q(location__icontains='to be confirmed') |
        Q(location__icontains='has yet to be')
    )
    
    total_valid = valid_components.count()
    total_all = Component.objects.count()
    
    print(f"Total components in database: {total_all}")
    print(f"Components with valid locations: {total_valid}")
    print(f"Components with invalid locations: {total_all - total_valid}")
    
    # Build full grouping
    print("\nBuilding location > description groups...")
    
    location_groups = valid_components.values(
        'location', 'description'
    ).annotate(
        component_count=Count('id'),
        unique_cmus=Count('cmu_id', distinct=True),
        unique_auctions=Count('auction_name', distinct=True),
        min_year=Min('delivery_year'),
        max_year=Max('delivery_year'),
        total_capacity=Sum('derated_capacity_mw')
    ).order_by('location', 'description')
    
    total_groups = len(location_groups)
    print(f"\nTotal location+description groups: {total_groups}")
    print(f"Reduction ratio: {total_valid}/{total_groups} = {total_valid/total_groups:.1f}:1")

def export_grouping_sample(output_file='location_grouping_sample.json'):
    """Export a sample of the grouping structure to JSON"""
    print("\n" + "="*80)
    print("EXPORTING SAMPLE GROUPING STRUCTURE")
    print("="*80)
    
    # Get locations with most components
    top_locations = Component.objects.exclude(
        location__in=['None', 'N/A', 'NA', 'TBC']
    ).values('location').annotate(
        count=Count('id')
    ).order_by('-count')[:20]
    
    export_data = {}
    
    for loc_data in top_locations:
        location = loc_data['location']
        components = Component.objects.filter(location=location).values(
            'id', 'description', 'cmu_id', 'auction_name', 
            'delivery_year', 'derated_capacity_mw', 'technology', 'company_name'
        )
        
        # Build hierarchical structure
        location_data = defaultdict(lambda: defaultdict(list))
        
        for comp in components:
            desc = comp['description'] or 'No Description'
            cmu = comp['cmu_id'] or 'No CMU'
            
            location_data[desc][cmu].append({
                'id': comp['id'],
                'auction': comp['auction_name'],
                'year': comp['delivery_year'],
                'capacity_mw': float(comp['derated_capacity_mw']) if comp['derated_capacity_mw'] else None,
                'technology': comp['technology'],
                'company': comp['company_name']
            })
        
        # Convert to regular dict for JSON
        export_data[location] = {
            'total_components': loc_data['count'],
            'descriptions': dict(location_data)
        }
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Exported {len(export_data)} locations to {output_file}")

def analyze_capacity_discrepancies():
    """Analyze where capacity values differ or are missing"""
    print("\n" + "="*80)
    print("CAPACITY DATA ANALYSIS")
    print("="*80)
    
    # Components with capacity data
    with_capacity = Component.objects.filter(derated_capacity_mw__isnull=False).count()
    without_capacity = Component.objects.filter(derated_capacity_mw__isnull=True).count()
    
    print(f"Components with capacity data: {with_capacity}")
    print(f"Components without capacity data: {without_capacity}")
    
    # Find CMUs with multiple components to check capacity distribution
    multi_component_cmus = Component.objects.values('cmu_id').annotate(
        count=Count('id'),
        total_capacity=Sum('derated_capacity_mw'),
        min_capacity=Min('derated_capacity_mw'),
        max_capacity=Max('derated_capacity_mw')
    ).filter(count__gt=1).order_by('-count')[:10]
    
    print(f"\nTop 10 CMUs with multiple components:")
    for cmu in multi_component_cmus:
        print(f"\nCMU: {cmu['cmu_id']}")
        print(f"  Components: {cmu['count']}")
        print(f"  Total capacity: {cmu['total_capacity']:.2f} MW" if cmu['total_capacity'] else "  Total capacity: Unknown")
        print(f"  Capacity range: {cmu['min_capacity']:.2f} - {cmu['max_capacity']:.2f} MW" 
              if cmu['min_capacity'] and cmu['max_capacity'] else "  Capacity range: Unknown")
        
        # Show individual components
        components = Component.objects.filter(cmu_id=cmu['cmu_id'])[:5]
        for comp in components:
            print(f"    - {comp.location[:50]}... : {comp.derated_capacity_mw} MW")

def find_complex_locations():
    """Find locations with complex multi-asset setups"""
    print("\n" + "="*80)
    print("COMPLEX MULTI-ASSET LOCATIONS")
    print("="*80)
    
    # Find locations with multiple technologies
    multi_tech = Component.objects.exclude(
        location__in=['None', 'N/A', 'NA', 'TBC']
    ).values('location').annotate(
        tech_count=Count('technology', distinct=True),
        company_count=Count('company_name', distinct=True),
        component_count=Count('id')
    ).filter(tech_count__gt=1).order_by('-tech_count')[:10]
    
    print("Locations with multiple technologies:")
    for loc in multi_tech:
        print(f"\n{loc['location']}")
        print(f"  Technologies: {loc['tech_count']}")
        print(f"  Companies: {loc['company_count']}")
        print(f"  Components: {loc['component_count']}")
        
        # Show technology breakdown
        techs = Component.objects.filter(
            location=loc['location']
        ).values('technology').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for tech in techs:
            print(f"    - {tech['technology']}: {tech['count']} components")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'battery':
            analyze_battery_components()
        elif sys.argv[1] == 'full':
            analyze_all_components_grouped()
        elif sys.argv[1] == 'export':
            export_grouping_sample()
        elif sys.argv[1] == 'capacity':
            analyze_capacity_discrepancies()
        elif sys.argv[1] == 'complex':
            find_complex_locations()
        elif sys.argv[1] == 'all':
            analyze_battery_components()
            analyze_all_components_grouped()
            analyze_capacity_discrepancies()
            find_complex_locations()
            export_grouping_sample()
    else:
        print("Usage: python test_location_grouping_expanded.py [battery|full|export|capacity|complex|all]")
        print("")
        print("Options:")
        print("  battery  - Analyze battery components specifically")
        print("  full     - Analyze full database with proper grouping")
        print("  export   - Export sample grouping structure to JSON")
        print("  capacity - Analyze capacity data discrepancies")
        print("  complex  - Find locations with multiple technologies/assets")
        print("  all      - Run all analyses")