#!/usr/bin/env python3
"""
Debug script to investigate AXLE ENERGY DSR filtering issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

from checker.models import LocationGroup, Component

def debug_axle_energy():
    print("🔍 DEBUGGING AXLE ENERGY DSR FILTERING")
    print("=" * 50)
    
    # 1. Find all LocationGroups that contain AXLE ENERGY
    print("\n1. LocationGroups containing AXLE ENERGY:")
    axle_locations = LocationGroup.objects.filter(companies__icontains='AXLE ENERGY')
    
    for lg in axle_locations:
        print(f"   📍 {lg.location} (ID: {lg.id})")
        print(f"      is_active: {lg.is_active}")
        print(f"      auction_years: {lg.auction_years}")
        print(f"      technologies: {list(lg.technologies.keys()) if lg.technologies else 'None'}")
        print(f"      companies: {list(lg.companies.keys()) if lg.companies else 'None'}")
        print()
    
    # 2. Check DSR-specific filtering
    print("\n2. AXLE ENERGY + DSR Technology filtering:")
    
    # All DSR locations with AXLE ENERGY
    dsr_axle_all = LocationGroup.objects.filter(
        technologies__icontains='DSR',
        companies__icontains='AXLE ENERGY'
    )
    print(f"   🔍 DSR + AXLE ENERGY (all): {dsr_axle_all.count()} locations")
    for lg in dsr_axle_all:
        print(f"      📍 {lg.location} - is_active: {lg.is_active}")
    
    # Active DSR locations with AXLE ENERGY  
    dsr_axle_active = LocationGroup.objects.filter(
        technologies__icontains='DSR',
        companies__icontains='AXLE ENERGY',
        is_active=True
    )
    print(f"   ✅ DSR + AXLE ENERGY (active): {dsr_axle_active.count()} locations")
    for lg in dsr_axle_active:
        print(f"      📍 {lg.location} - is_active: {lg.is_active}")
    
    # Inactive DSR locations with AXLE ENERGY
    dsr_axle_inactive = LocationGroup.objects.filter(
        technologies__icontains='DSR',
        companies__icontains='AXLE ENERGY',
        is_active=False
    )
    print(f"   ❌ DSR + AXLE ENERGY (inactive): {dsr_axle_inactive.count()} locations")
    for lg in dsr_axle_inactive:
        print(f"      📍 {lg.location} - is_active: {lg.is_active}")
    
    # 3. Check individual Components for AXLE ENERGY + DSR
    print("\n3. Individual Components (AXLE ENERGY + DSR):")
    axle_dsr_components = Component.objects.filter(
        company_name__icontains='AXLE ENERGY',
        technology__icontains='DSR'
    )
    
    print(f"   📊 Total AXLE ENERGY DSR components: {axle_dsr_components.count()}")
    
    # Group by location and check auction years
    from collections import defaultdict
    locations_data = defaultdict(list)
    
    for comp in axle_dsr_components:
        locations_data[comp.location].append({
            'auction_name': comp.auction_name,
            'delivery_year': comp.delivery_year,
            'cmu_id': comp.cmu_id
        })
    
    for location, components in locations_data.items():
        print(f"   📍 {location}:")
        for comp in components:
            print(f"      - {comp['cmu_id']}: {comp['auction_name']} (delivery: {comp['delivery_year']})")
        
        # Check if this location should be active based on auction years
        auction_years = [comp['auction_name'] for comp in components if comp['auction_name']]
        active_patterns = ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']
        has_active = any(
            any(pattern in year for pattern in active_patterns)
            for year in auction_years
        )
        print(f"      🎯 Should be active: {has_active} (auction years: {auction_years})")
        
        # Check what LocationGroup says
        try:
            lg = LocationGroup.objects.get(location=location)
            print(f"      🏢 LocationGroup is_active: {lg.is_active}")
        except LocationGroup.DoesNotExist:
            print(f"      ❌ No LocationGroup found for {location}")
        print()

if __name__ == "__main__":
    debug_axle_energy()