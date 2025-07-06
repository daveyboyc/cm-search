#!/usr/bin/env python3
"""
Test that database-level filtering produces IDENTICAL results to Python-based filtering
for company_detail_optimized view.
"""
import os
import sys
import django
from collections import defaultdict

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.db.models import Q, Count, Sum
from checker.models import LocationGroup, Component
from checker.utils import normalize


def get_company_locations_python_filtering(company_name, status_filter='all', auction_filter='all'):
    """
    Current implementation - uses Python loops for filtering
    This is what company_detail_optimized currently does
    """
    # Find LocationGroups for this company
    location_groups = LocationGroup.objects.filter(
        companies__has_key=company_name
    )
    
    # Apply status filtering (PYTHON LOOPS - CURRENT METHOD)
    if status_filter == 'active':
        filtered_ids = []
        for lg in location_groups:
            if lg.auction_years:
                is_active = False
                for year_str in lg.auction_years:
                    if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                        is_active = True
                        break
                if is_active:
                    filtered_ids.append(lg.id)
        location_groups = location_groups.filter(id__in=filtered_ids)
        
    elif status_filter == 'inactive':
        filtered_ids = []
        for lg in location_groups:
            if lg.auction_years:
                is_inactive = True
                for year_str in lg.auction_years:
                    if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                        is_inactive = False
                        break
                if is_inactive:
                    filtered_ids.append(lg.id)
            else:
                # No auction years = inactive
                filtered_ids.append(lg.id)
        location_groups = location_groups.filter(id__in=filtered_ids)
    
    # Apply auction year filter (PYTHON LOOPS - CURRENT METHOD)
    if auction_filter != 'all':
        filtered_ids = []
        for lg in location_groups:
            if lg.auction_years and auction_filter in lg.auction_years:
                filtered_ids.append(lg.id)
        location_groups = location_groups.filter(id__in=filtered_ids)
    
    return location_groups.order_by('-normalized_capacity_mw')


def get_company_locations_database_filtering(company_name, status_filter='all', auction_filter='all'):
    """
    Optimized implementation - uses database-level filtering
    This is what we want to implement
    """
    # Find LocationGroups for this company
    location_groups = LocationGroup.objects.filter(
        companies__has_key=company_name
    )
    
    # Apply status filtering (DATABASE LEVEL - OPTIMIZED)
    if status_filter == 'active':
        # Use the pre-calculated is_active field
        location_groups = location_groups.filter(is_active=True)
        
    elif status_filter == 'inactive':
        # Use the pre-calculated is_active field
        location_groups = location_groups.filter(is_active=False)
    
    # Apply auction year filter (DATABASE LEVEL - OPTIMIZED)
    if auction_filter != 'all':
        location_groups = location_groups.filter(
            auction_years__icontains=auction_filter
        )
    
    return location_groups.order_by('-normalized_capacity_mw')


def compare_results(company_name, status_filter='all', auction_filter='all'):
    """
    Compare results from both methods
    """
    print(f"\n🔍 Testing: {company_name}")
    print(f"   Status filter: {status_filter}")
    print(f"   Auction filter: {auction_filter}")
    print("-" * 60)
    
    # Get results from both methods
    python_results = get_company_locations_python_filtering(company_name, status_filter, auction_filter)
    db_results = get_company_locations_database_filtering(company_name, status_filter, auction_filter)
    
    # Convert to sets of IDs for comparison
    python_ids = set(python_results.values_list('id', flat=True))
    db_ids = set(db_results.values_list('id', flat=True))
    
    # Compare counts
    print(f"Python filtering: {len(python_ids)} locations")
    print(f"Database filtering: {len(db_ids)} locations")
    
    # Check if results match
    if python_ids == db_ids:
        print("✅ RESULTS MATCH EXACTLY!")
    else:
        print("❌ RESULTS DO NOT MATCH!")
        
        # Show differences
        only_in_python = python_ids - db_ids
        only_in_db = db_ids - python_ids
        
        if only_in_python:
            print(f"   Only in Python results: {only_in_python}")
            for lg_id in list(only_in_python)[:3]:
                lg = LocationGroup.objects.get(id=lg_id)
                print(f"     - {lg.location}: auction_years={lg.auction_years}, is_active={lg.is_active}")
        
        if only_in_db:
            print(f"   Only in DB results: {only_in_db}")
            for lg_id in list(only_in_db)[:3]:
                lg = LocationGroup.objects.get(id=lg_id)
                print(f"     - {lg.location}: auction_years={lg.auction_years}, is_active={lg.is_active}")
    
    # Compare performance
    import time
    
    # Time Python method
    start = time.time()
    list(python_results)  # Force evaluation
    python_time = time.time() - start
    
    # Time database method
    start = time.time()
    list(db_results)  # Force evaluation
    db_time = time.time() - start
    
    print(f"\nPerformance:")
    print(f"  Python filtering: {python_time:.3f}s")
    print(f"  Database filtering: {db_time:.3f}s")
    print(f"  Speedup: {python_time/db_time:.1f}x faster")
    
    return python_ids == db_ids


def run_comprehensive_test():
    """
    Run tests for multiple companies and filter combinations
    """
    print("🧪 COMPREHENSIVE FILTERING COMPARISON TEST")
    print("=" * 60)
    
    # Get some test companies
    test_companies = []
    
    # Find companies with varying numbers of locations
    companies_with_counts = Component.objects.values('company_name').annotate(
        count=Count('id')
    ).filter(company_name__isnull=False).order_by('-count')[:5]
    
    for company_data in companies_with_counts:
        company_name = company_data['company_name']
        # Check if this company exists in LocationGroup
        if LocationGroup.objects.filter(companies__has_key=company_name).exists():
            test_companies.append(company_name)
            if len(test_companies) >= 3:
                break
    
    if not test_companies:
        print("❌ No companies found for testing!")
        return
    
    # Test combinations
    test_cases = [
        ('all', 'all'),
        ('active', 'all'),
        ('inactive', 'all'),
        ('active', 'T-4 2024-25'),
        ('inactive', 'T-4 2023-24'),
    ]
    
    all_match = True
    
    for company in test_companies:
        for status_filter, auction_filter in test_cases:
            matches = compare_results(company, status_filter, auction_filter)
            if not matches:
                all_match = False
    
    print("\n" + "=" * 60)
    if all_match:
        print("✅ ALL TESTS PASSED! Database filtering produces IDENTICAL results!")
        print("\n🎯 It is SAFE to implement database-level filtering.")
    else:
        print("❌ Some tests failed. Need to investigate the differences.")


def check_is_active_field():
    """
    Verify that is_active field is correctly populated
    """
    print("\n📊 CHECKING is_active FIELD ACCURACY")
    print("=" * 60)
    
    # Sample some LocationGroups
    sample = LocationGroup.objects.all()[:20]
    
    mismatches = 0
    for lg in sample:
        # Calculate what is_active should be
        expected_active = False
        if lg.auction_years:
            for year_str in lg.auction_years:
                if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                    expected_active = True
                    break
        
        if lg.is_active != expected_active:
            mismatches += 1
            print(f"❌ Mismatch: {lg.location}")
            print(f"   auction_years: {lg.auction_years}")
            print(f"   is_active: {lg.is_active} (expected: {expected_active})")
    
    if mismatches == 0:
        print("✅ All sampled LocationGroups have correct is_active values!")
    else:
        print(f"❌ Found {mismatches} mismatches in is_active field")
        print("   You may need to run build_location_groups command to update")


if __name__ == "__main__":
    # First check if is_active field is accurate
    check_is_active_field()
    
    # Then run comprehensive comparison
    run_comprehensive_test()
    
    print("\n💡 NEXT STEPS:")
    print("1. If all tests pass, implement database filtering in views_company_optimized.py")
    print("2. Test the updated view in browser to verify UI works correctly")
    print("3. Roll out to other views (technology, search)")