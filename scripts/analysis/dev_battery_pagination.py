#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.services.data_access import get_components_from_database
from checker.services.component_search import group_by_location
import time

print("Testing battery search pagination fix...")
print("=" * 60)

# First, get the total count
print("\n1. Getting total battery component count...")
start = time.time()
_, metadata = get_components_from_database(
    search_term="battery",
    page=1,
    per_page=1,
    query_type="general"
)
total_count = metadata.get("total_count", 0)
print(f"Total battery components in database: {total_count}")
print(f"Query time: {time.time() - start:.2f}s")

# Now fetch components with different limits
test_limits = [100, 500, 1000, 3000, 5000]

for limit in test_limits:
    if limit > total_count:
        continue
        
    print(f"\n2. Testing with limit={limit}...")
    start = time.time()
    components, _ = get_components_from_database(
        search_term="battery",
        page=1,
        per_page=limit,
        query_type="general"
    )
    fetch_time = time.time() - start
    
    # Group by location
    start = time.time()
    grouped = group_by_location(components)
    group_time = time.time() - start
    
    print(f"   - Fetched {len(components)} components in {fetch_time:.2f}s")
    print(f"   - Grouped into {len(grouped)} locations in {group_time:.2f}s")
    print(f"   - Average components per location: {len(components)/len(grouped):.1f}")
    
    # Calculate pagination
    groups_per_page = 10
    total_pages = (len(grouped) + groups_per_page - 1) // groups_per_page
    print(f"   - With {groups_per_page} groups per page = {total_pages} pages")
    
    # Show percentage of total
    pct = (len(components) / total_count) * 100
    print(f"   - Showing {pct:.1f}% of total components")

print("\n" + "=" * 60)
print("CONCLUSION:")
print(f"To show all {total_count} battery components properly grouped,")
print(f"we need to fetch at least {min(total_count, 5000)} components.")
print("Current limit of 500-3000 is too low for accurate pagination.")