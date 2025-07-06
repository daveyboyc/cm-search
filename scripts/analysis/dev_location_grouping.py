#!/usr/bin/env python
import os
import sys
import django
from collections import defaultdict

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count, Sum, Q

def analyze_location_grouping(location_filter=None, limit=None):
    """
    Analyze how components would group by location > description > cmu_id > auction_year
    """
    # Build query
    query = Component.objects.all()
    if location_filter:
        query = query.filter(location__icontains=location_filter)
    
    if limit:
        query = query[:limit]
    
    # Fetch components
    components = query.select_related().values(
        'id', 'location', 'description', 'cmu_id', 'auction_name', 
        'delivery_year', 'derated_capacity_mw', 'company_name', 'technology'
    )
    
    # Build hierarchical structure
    location_groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    total_components = 0
    for comp in components:
        location = comp['location'] or 'Unknown Location'
        description = comp['description'] or 'No Description'
        cmu_id = comp['cmu_id'] or 'No CMU ID'
        auction = comp['auction_name'] or 'No Auction'
        
        location_groups[location][description][cmu_id].append({
            'id': comp['id'],
            'auction': auction,
            'year': comp['delivery_year'],
            'capacity': comp['derated_capacity_mw'],
            'company': comp['company_name'],
            'technology': comp['technology']
        })
        total_components += 1
    
    return location_groups, total_components

def print_analysis(location_groups, total_components):
    """Print the analysis results"""
    print(f"\nANALYSIS RESULTS")
    print("=" * 80)
    print(f"Total components analyzed: {total_components}")
    print(f"Unique locations: {len(location_groups)}")
    
    # Count total unique descriptions
    total_descriptions = sum(len(descs) for descs in location_groups.values())
    print(f"Total unique location+description combinations: {total_descriptions}")
    
    print("\nDETAILED BREAKDOWN:")
    print("-" * 80)
    
    # Show up to 5 locations with multiple descriptions
    multi_desc_locations = [(loc, descs) for loc, descs in location_groups.items() if len(descs) > 1]
    
    if multi_desc_locations:
        print("\nLOCATIONS WITH MULTIPLE DESCRIPTIONS (showing up to 5):")
        for i, (location, descriptions) in enumerate(multi_desc_locations[:5]):
            print(f"\n{i+1}. {location}")
            print(f"   Has {len(descriptions)} unique descriptions:")
            
            for j, (desc, cmu_ids) in enumerate(descriptions.items()):
                if j < 3:  # Show first 3 descriptions
                    print(f"   - {desc[:80]}...")
                    total_components_in_desc = sum(len(comps) for comps in cmu_ids.values())
                    print(f"     CMU IDs: {len(cmu_ids)}, Total components: {total_components_in_desc}")
                    
                    # Show capacity range if available
                    all_capacities = [c['capacity'] for cmu_comps in cmu_ids.values() 
                                    for c in cmu_comps if c['capacity']]
                    if all_capacities:
                        print(f"     Capacity range: {min(all_capacities):.2f} - {max(all_capacities):.2f} MW")
            
            if len(descriptions) > 3:
                print(f"   ... and {len(descriptions) - 3} more descriptions")
    
    print("\n" + "=" * 80)
    print("GROUPING EFFICIENCY:")
    print(f"Original components: {total_components}")
    print(f"After location grouping: {len(location_groups)} groups")
    print(f"After location+description grouping: {total_descriptions} groups")
    print(f"Reduction ratio: {total_components / total_descriptions:.1f}:1")

def test_specific_location(location_name):
    """Test grouping for a specific location"""
    print(f"\nTEST CASE: {location_name}")
    print("=" * 80)
    
    components = Component.objects.filter(
        location__icontains=location_name
    ).values(
        'id', 'location', 'description', 'cmu_id', 'auction_name',
        'delivery_year', 'derated_capacity_mw', 'company_name'
    )
    
    if not components:
        print(f"No components found for location: {location_name}")
        return
    
    # Group by description
    by_description = defaultdict(list)
    for comp in components:
        desc = comp['description'] or 'No Description'
        by_description[desc].append(comp)
    
    print(f"Found {len(components)} components at this location")
    print(f"Unique descriptions: {len(by_description)}")
    
    for desc, comps in by_description.items():
        print(f"\n  Description: {desc}")
        print(f"  Components: {len(comps)}")
        
        # Group by CMU ID within this description
        by_cmu = defaultdict(list)
        for comp in comps:
            by_cmu[comp['cmu_id']].append(comp)
        
        for cmu_id, cmu_comps in by_cmu.items():
            print(f"    CMU ID: {cmu_id}")
            for comp in cmu_comps:
                print(f"      - {comp['auction_name']} ({comp['delivery_year']}): {comp['derated_capacity_mw']} MW")

if __name__ == "__main__":
    print("LOCATION GROUPING ANALYSIS")
    print("Testing how components would group by: Location > Description > CMU ID > Auction Year")
    
    # Test 1: Analyze a sample of all components
    print("\n1. ANALYZING FIRST 1000 COMPONENTS...")
    location_groups, total = analyze_location_grouping(limit=1000)
    print_analysis(location_groups, total)
    
    # Test 2: Look for Imperial College specifically
    print("\n2. SPECIFIC LOCATION TEST: Imperial College")
    test_specific_location("Imperial College")
    
    # Test 3: Look for locations with "Engine" in description
    print("\n3. SEARCHING FOR 'ENGINE' PATTERN...")
    engine_components = Component.objects.filter(
        description__icontains='engine'
    ).values('location', 'description', 'cmu_id').distinct()[:20]
    
    print(f"Found {len(engine_components)} unique location+description+cmu combinations with 'engine'")
    for comp in engine_components[:10]:
        print(f"  - {comp['location']}: {comp['description']}")
    
    # Test 4: Find locations with most components
    print("\n4. LOCATIONS WITH MOST COMPONENTS...")
    top_locations = Component.objects.values('location').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    for loc in top_locations:
        print(f"  {loc['location']}: {loc['count']} components")
        # Check how many unique descriptions
        unique_descs = Component.objects.filter(
            location=loc['location']
        ).values('description').distinct().count()
        print(f"    → {unique_descs} unique descriptions")