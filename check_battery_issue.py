#!/usr/bin/env python
"""Check what's happening with battery search"""
import os
import django
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Q

print("🔍 Checking 'battery' search issue")
print("=" * 50)

# Check how many battery components exist
query = "battery"
filter_obj = (
    Q(location__icontains=query) |
    Q(county__icontains=query) |
    Q(outward_code__icontains=query) |
    Q(description__icontains=query) |
    Q(technology__icontains=query) |
    Q(company_name__icontains=query) |
    Q(cmu_id__icontains=query)
)

total_count = Component.objects.filter(filter_obj).count()
print(f"\n1️⃣ Total components matching 'battery': {total_count}")

# Check how the pagination works
from django.core.paginator import Paginator

# Get first 100 components
components = list(Component.objects.filter(filter_obj).order_by('-delivery_year')[:100])
print(f"\n2️⃣ First 100 components retrieved")

# Group by location
from collections import defaultdict
location_groups = defaultdict(list)
for comp in components:
    location_groups[comp.location].append(comp)

print(f"\n3️⃣ These 100 components group into {len(location_groups)} locations")

# Show the issue
print(f"\n❌ THE ISSUE:")
print(f"   - Database has {total_count} battery components")
print(f"   - But we're only fetching 100 at a time")
print(f"   - These 100 group into ~{len(location_groups)} location groups")
print(f"   - So pagination shows ~{len(location_groups)//10} pages instead of {total_count//10}")

print(f"\n💡 The problem is in component_search.py:")
print(f"   Line ~709: Fetches limited components (100) instead of all")
print(f"   This was meant to optimize, but breaks pagination!")

# Check what happens with location sort
print(f"\n4️⃣ When sorting by location:")
components_by_loc = Component.objects.filter(filter_obj).order_by('location')[:100]
locations_in_first_100 = set(c.location for c in components_by_loc)
print(f"   First 100 components are from {len(locations_in_first_100)} locations")
print(f"   This explains why location sort shows even fewer results!"

print(f"\n🔧 FIX NEEDED:")
print(f"   component_search.py needs to fetch ALL matching components")
print(f"   for proper grouping and pagination, not just 100")