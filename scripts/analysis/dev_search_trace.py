#!/usr/bin/env python
"""Trace through the search to see what's happening."""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

# Enable logging to see what's happening
import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

# Import what we need
from django.test import RequestFactory
from checker.services.location_group_check import should_use_location_groups
from checker.services.component_search import search_components_service

print("\n=== SEARCH TRACE TEST ===\n")

# Step 1: Check if LocationGroups should be used
print("1. Checking should_use_location_groups():")
use_lg = should_use_location_groups()
print(f"   Result: {use_lg}")

# Step 2: Check if functions are available
print("\n2. Checking if search_locations is available:")
try:
    from checker.services.location_search import search_locations
    print("   ✓ search_locations imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import: {e}")

# Step 3: Check component_search.py has the functions
print("\n3. Checking component_search.py imports:")
from checker.services import component_search
print(f"   should_use_location_groups: {hasattr(component_search, 'should_use_location_groups')}")
print(f"   search_locations: {hasattr(component_search, 'search_locations')}")

# Step 4: Try a direct location search
print("\n4. Testing direct location search:")
try:
    from checker.services.location_search import search_locations
    location_groups, total = search_locations(
        query='battery',
        page=1, 
        per_page=10,
        sort_by='relevance',
        sort_order='desc'
    )
    print(f"   ✓ Direct search returned {len(location_groups)} LocationGroups")
    if location_groups:
        print(f"   First result: {location_groups[0].location}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Mock a request and trace the search
print("\n5. Testing search_components_service:")
factory = RequestFactory()
request = factory.get('/search/', {'q': 'battery', 'page': 1, 'per_page': 10})

# Add mock user
class MockUser:
    is_authenticated = False
request.user = MockUser()

# Patch the search function to trace execution
original_search = search_components_service

def traced_search(request, **kwargs):
    print("   → search_components_service called")
    
    # Check inside the function
    from checker.services.location_group_check import should_use_location_groups
    from checker.services.component_search import search_locations
    
    print(f"   → should_use_location_groups: {should_use_location_groups()}")
    print(f"   → search_locations available: {search_locations is not None}")
    
    return original_search(request, **kwargs)

# Call the traced search
from checker.services import component_search
component_search.search_components_service = traced_search

try:
    result = traced_search(request, return_data_only=True)
    print(f"   → Search completed")
    print(f"   → Total count: {result.get('total_count', 0)}")
except Exception as e:
    print(f"   ✗ Error during search: {e}")
    import traceback
    traceback.print_exc()