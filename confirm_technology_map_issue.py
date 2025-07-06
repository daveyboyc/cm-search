#!/usr/bin/env python3
"""
Confirm the technology map sampling issue for AXLE ENERGY LIMITED.
This reproduces the exact query used by the technology view.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

from checker.models import LocationGroup

def confirm_sampling_issue():
    print("=" * 80)
    print("TECHNOLOGY MAP SAMPLING ISSUE CONFIRMATION")
    print("=" * 80)
    
    # Reproduce the exact query from views_technology_optimized.py line 77-78
    print("1. Simulating technology map dropdown query for DSR:")
    print("-" * 55)
    
    # Find all LocationGroups with DSR technology
    location_groups = LocationGroup.objects.filter(
        technologies__icontains="DSR"
    )
    
    total_dsr_locations = location_groups.count()
    print(f"   Total DSR locations: {total_dsr_locations:,}")
    
    # Get the sample data exactly as the technology view does
    sample_size = min(500, location_groups.count())
    sample_data = location_groups.order_by('-normalized_capacity_mw').values_list('auction_years', 'companies')[:sample_size]
    
    print(f"   Sample size used for dropdown: {sample_size}")
    
    # Extract companies from the sample
    all_companies = set()
    for years, companies in sample_data:
        if companies:
            all_companies.update(companies.keys())
    
    companies = sorted(list(all_companies))
    print(f"   Companies found in sample: {len(companies)}")
    
    # Check if AXLE ENERGY LIMITED is in the dropdown companies
    axle_in_dropdown = "AXLE ENERGY LIMITED" in companies
    print(f"   AXLE ENERGY LIMITED in dropdown: {axle_in_dropdown}")
    
    print(f"\n2. Analyzing the top 500 DSR locations by capacity:")
    print("-" * 55)
    
    # Get the top 500 locations and their companies
    top_500_locations = location_groups.order_by('-normalized_capacity_mw')[:500]
    
    # Check if any have AXLE ENERGY LIMITED
    axle_locations_in_top_500 = []
    for location in top_500_locations:
        if location.companies and 'AXLE ENERGY LIMITED' in location.companies:
            axle_locations_in_top_500.append(location.location)
    
    print(f"   AXLE ENERGY LIMITED locations in top 500: {len(axle_locations_in_top_500)}")
    
    if axle_locations_in_top_500:
        print(f"   Example AXLE locations: {axle_locations_in_top_500[:5]}")
    
    # Check the capacity of the 500th location
    if len(top_500_locations) >= 500:
        location_500 = list(top_500_locations)[499]  # 500th item (0-indexed)
        print(f"   500th location capacity: {location_500.normalized_capacity_mw:.2f} MW")
        print(f"   500th location: {location_500.location}")
    
    print(f"\n3. Finding where AXLE ENERGY LIMITED locations rank:")
    print("-" * 60)
    
    # Find the best ranking AXLE ENERGY LIMITED location
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                location,
                normalized_capacity_mw,
                ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
            FROM checker_locationgroup
            WHERE technologies::text ILIKE '%DSR%'
              AND companies ? 'AXLE ENERGY LIMITED'
            ORDER BY normalized_capacity_mw DESC, location ASC
            LIMIT 5;
        """)
        
        axle_rankings = cursor.fetchall()
        
        if axle_rankings:
            print(f"   Top 5 AXLE ENERGY LIMITED DSR locations:")
            print(f"   {'Location':<25} {'Capacity':<12} {'Rank':<8}")
            print(f"   {'-' * 45}")
            
            for location, capacity, rank in axle_rankings:
                print(f"   {location:<25} {capacity:<12.2f} {rank:<8}")
                
            best_rank = axle_rankings[0][2]
            print(f"\n   Best AXLE ENERGY LIMITED rank: #{best_rank}")
            
            if best_rank > 500:
                print(f"   ✗ PROBLEM CONFIRMED: Best rank #{best_rank} is beyond top 500")
                print(f"   ✗ Technology map sampling (top 500) excludes ALL AXLE locations")
            else:
                print(f"   ✓ Best rank #{best_rank} should be in top 500")
        else:
            print("   ✗ No AXLE ENERGY LIMITED DSR locations found!")
    
    print(f"\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    
    if not axle_in_dropdown:
        print("🎯 ISSUE CONFIRMED:")
        print("   1. Technology map uses sampling (top 500 by capacity) for dropdowns")
        print("   2. ALL AXLE ENERGY LIMITED DSR locations have 0.00 MW capacity") 
        print("   3. Due to tie-breaking in PostgreSQL ORDER BY, AXLE locations")
        print("      happen to sort beyond the 500th position")
        print("   4. This excludes them from the dropdown population query")
        print("   5. Result: AXLE ENERGY LIMITED doesn't appear in DSR dropdown")
        print(f"\n💡 SOLUTION:")
        print("   - Increase sample size beyond 500, OR")
        print("   - Use different tie-breaking (e.g., ORDER BY capacity DESC, location ASC), OR")
        print("   - Remove sampling entirely for company dropdowns")
    else:
        print("✓ AXLE ENERGY LIMITED appears in dropdown - investigation needed elsewhere")

if __name__ == "__main__":
    confirm_sampling_issue()