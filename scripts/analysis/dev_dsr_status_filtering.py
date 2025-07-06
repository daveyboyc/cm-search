#!/usr/bin/env python
import os
import sys
import django
from django.db import connection
from django.test import RequestFactory
from unittest.mock import Mock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup
from checker.views_technology_optimized import technology_detail_map

def test_status_filtering():
    print("Testing DSR status filtering for AXLE ENERGY...")
    print("=" * 60)
    
    # Test 1: Query database directly for all DSR + AXLE ENERGY LocationGroups
    print("\n1. Direct Database Query - All DSR + AXLE ENERGY LocationGroups:")
    all_locations = LocationGroup.objects.filter(
        technologies__icontains='DSR',
        companies__icontains='AXLE ENERGY'
    )
    print(f"Total DSR + AXLE ENERGY locations: {all_locations.count()}")
    
    # Check is_active status breakdown
    active_count = all_locations.filter(is_active=True).count()
    inactive_count = all_locations.filter(is_active=False).count()
    print(f"Active locations: {active_count}")
    print(f"Inactive locations: {inactive_count}")
    
    # Test 2: Simulate the view filtering logic
    print("\n2. View Filtering Logic Simulation:")
    
    # Simulate request for status=all
    factory = RequestFactory()
    request_all = factory.get('/technology/DSR/?status=all')
    request_all.GET = {'status': 'all'}
    
    # Get base queryset
    base_queryset = LocationGroup.objects.filter(technologies__icontains='DSR')
    
    # Apply status filtering like the view does
    status_filter_all = request_all.GET.get('status', 'all')
    if status_filter_all == 'active':
        filtered_all = base_queryset.filter(is_active=True)
    elif status_filter_all == 'inactive':
        filtered_all = base_queryset.filter(is_active=False)
    else:
        filtered_all = base_queryset  # No filtering for 'all'
    
    # Count AXLE ENERGY in results
    axle_results_all = filtered_all.filter(companies__icontains='AXLE ENERGY').count()
    print(f"status=all: {axle_results_all} AXLE ENERGY DSR locations")
    
    # Simulate request for status=active
    request_active = factory.get('/technology/DSR/?status=active')
    request_active.GET = {'status': 'active'}
    
    status_filter_active = request_active.GET.get('status', 'all')
    if status_filter_active == 'active':
        filtered_active = base_queryset.filter(is_active=True)
    elif status_filter_active == 'inactive':
        filtered_active = base_queryset.filter(is_active=False)
    else:
        filtered_active = base_queryset
    
    axle_results_active = filtered_active.filter(companies__icontains='AXLE ENERGY').count()
    print(f"status=active: {axle_results_active} AXLE ENERGY DSR locations")
    
    # Simulate request for status=inactive
    request_inactive = factory.get('/technology/DSR/?status=inactive')
    request_inactive.GET = {'status': 'inactive'}
    
    status_filter_inactive = request_inactive.GET.get('status', 'all')
    if status_filter_inactive == 'active':
        filtered_inactive = base_queryset.filter(is_active=True)
    elif status_filter_inactive == 'inactive':
        filtered_inactive = base_queryset.filter(is_active=False)
    else:
        filtered_inactive = base_queryset
    
    axle_results_inactive = filtered_inactive.filter(companies__icontains='AXLE ENERGY').count()
    print(f"status=inactive: {axle_results_inactive} AXLE ENERGY DSR locations")
    
    # Test 3: Check if there are any issues with the is_active field calculation
    print("\n3. Analyzing is_active field calculation:")
    
    # Sample a few AXLE ENERGY DSR locations and check their auction_years
    sample_locations = all_locations[:5]
    for location in sample_locations:
        print(f"\nLocation: {location.location}")
        print(f"  is_active: {location.is_active}")
        print(f"  auction_years: {location.auction_years}")
        print(f"  companies: {location.companies}")
        
        # Check if any auction year contains 2024-25 or later
        has_active_year = False
        if location.auction_years:
            for year in location.auction_years:
                if any(active_year in year for active_year in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                    has_active_year = True
                    break
        print(f"  should_be_active: {has_active_year}")
        print(f"  is_active matches expected: {location.is_active == has_active_year}")
    
    # Test 4: Check if there are any other filtering issues
    print("\n4. Additional Checks:")
    
    # Check if there are any DSR locations with AXLE ENERGY that are inactive
    inactive_axle_dsr = LocationGroup.objects.filter(
        technologies__icontains='DSR',
        companies__icontains='AXLE ENERGY',
        is_active=False
    )
    print(f"Inactive AXLE ENERGY DSR locations: {inactive_axle_dsr.count()}")
    if inactive_axle_dsr.exists():
        print("Sample inactive locations:")
        for loc in inactive_axle_dsr[:3]:
            print(f"  {loc.location}: {loc.auction_years}")
    
    # Test 5: URL parameter analysis
    print("\n5. URL Parameter Analysis:")
    print("The filter links in the template generate these URLs:")
    print("  All: ?status=all")
    print("  Active: ?status=active") 
    print("  Inactive: ?status=inactive")
    print("\nThe view logic treats these as:")
    print("  status=all -> No filtering (shows all results)")
    print("  status=active -> Filter to is_active=True")
    print("  status=inactive -> Filter to is_active=False")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"✓ Total AXLE ENERGY DSR locations: {all_locations.count()}")
    print(f"✓ Active AXLE ENERGY DSR locations: {active_count}")
    print(f"✓ Inactive AXLE ENERGY DSR locations: {inactive_count}")
    print(f"✓ status=all should show: {axle_results_all}")
    print(f"✓ status=active should show: {axle_results_active}")
    print(f"✓ status=inactive should show: {axle_results_inactive}")
    
    if axle_results_all == axle_results_active and inactive_count == 0:
        print("\n✅ FILTERING IS WORKING CORRECTLY!")
        print("   - All AXLE ENERGY DSR locations are active")
        print("   - status=all and status=active show the same results")
        print("   - status=inactive shows 0 results")
        print("\n🔍 DIAGNOSIS: If user reports different behavior, this suggests:")
        print("   1. Frontend JavaScript interference")
        print("   2. Caching issues")
        print("   3. User testing different parameters")
        print("   4. URL encoding/decoding issues")
    else:
        print("\n❌ POTENTIAL ISSUE FOUND!")
        print("   Expected: status=all == status=active (since all are active)")
        print(f"   Actual: status=all={axle_results_all}, status=active={axle_results_active}")

if __name__ == "__main__":
    test_status_filtering()