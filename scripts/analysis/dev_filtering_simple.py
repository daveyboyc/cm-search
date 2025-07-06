#!/usr/bin/env python3
"""
Simple test to verify database filtering works correctly.
Run this with: python manage.py shell < test_filtering_simple.py
"""

from django.db.models import Q, Count
from checker.models import LocationGroup, Component

print("🧪 TESTING DATABASE VS PYTHON FILTERING")
print("=" * 50)

# Find a test company
test_company = Component.objects.filter(
    company_name__isnull=False
).values('company_name').annotate(
    count=Count('id')
).first()

if not test_company:
    print("❌ No companies found")
    exit()

company_name = test_company['company_name']
print(f"Testing company: {company_name}")

# Check if company exists in LocationGroup
company_locations = LocationGroup.objects.filter(
    companies__has_key=company_name
)

if not company_locations.exists():
    print("❌ Company not found in LocationGroup")
    exit()

print(f"Total locations: {company_locations.count()}")

# TEST 1: Active filtering
print("\n1. Testing ACTIVE filtering:")
print("-" * 30)

# Python method (current)
python_active_ids = []
for lg in company_locations:
    if lg.auction_years:
        is_active = False
        for year_str in lg.auction_years:
            if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                is_active = True
                break
        if is_active:
            python_active_ids.append(lg.id)

# Database method (optimized)
db_active = company_locations.filter(is_active=True)
db_active_ids = list(db_active.values_list('id', flat=True))

print(f"Python filtering: {len(python_active_ids)} active locations")
print(f"Database filtering: {len(db_active_ids)} active locations")

if set(python_active_ids) == set(db_active_ids):
    print("✅ ACTIVE filtering matches!")
else:
    print("❌ ACTIVE filtering differs!")
    print(f"Difference: {set(python_active_ids) ^ set(db_active_ids)}")

# TEST 2: Inactive filtering
print("\n2. Testing INACTIVE filtering:")
print("-" * 30)

# Python method (current)
python_inactive_ids = []
for lg in company_locations:
    if lg.auction_years:
        is_inactive = True
        for year_str in lg.auction_years:
            if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                is_inactive = False
                break
        if is_inactive:
            python_inactive_ids.append(lg.id)
    else:
        # No auction years = inactive
        python_inactive_ids.append(lg.id)

# Database method (optimized)
db_inactive = company_locations.filter(is_active=False)
db_inactive_ids = list(db_inactive.values_list('id', flat=True))

print(f"Python filtering: {len(python_inactive_ids)} inactive locations")
print(f"Database filtering: {len(db_inactive_ids)} inactive locations")

if set(python_inactive_ids) == set(db_inactive_ids):
    print("✅ INACTIVE filtering matches!")
else:
    print("❌ INACTIVE filtering differs!")
    print(f"Difference: {set(python_inactive_ids) ^ set(db_inactive_ids)}")

# TEST 3: Check a few examples
print("\n3. Checking individual examples:")
print("-" * 30)

for lg in company_locations[:3]:
    # Calculate expected is_active
    expected_active = False
    if lg.auction_years:
        for year_str in lg.auction_years:
            if any(pattern in year_str for pattern in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                expected_active = True
                break
    
    print(f"Location: {lg.location}")
    print(f"  auction_years: {lg.auction_years}")
    print(f"  is_active (field): {lg.is_active}")
    print(f"  is_active (calculated): {expected_active}")
    
    if lg.is_active == expected_active:
        print("  ✅ Matches")
    else:
        print("  ❌ Mismatch!")
    print()

print("=" * 50)
print("🎯 CONCLUSION:")
if (set(python_active_ids) == set(db_active_ids) and 
    set(python_inactive_ids) == set(db_inactive_ids)):
    print("✅ Database filtering produces IDENTICAL results!")
    print("✅ Safe to implement optimization!")
else:
    print("❌ Results differ - need to investigate!")