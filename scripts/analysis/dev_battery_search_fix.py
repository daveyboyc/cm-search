#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.test import RequestFactory
from checker.services.component_search import search_components_service
import time

# Create a mock request
factory = RequestFactory()

print("Testing battery search with new pagination fix...")
print("=" * 60)

# Test page 1
request = factory.get('/search/?q=battery&page=1&per_page=10&sort_by=newest')
start = time.time()
result = search_components_service(request, return_data_only=True)
elapsed = time.time() - start

print(f"\nPage 1 Results:")
print(f"Search time: {elapsed:.2f}s")
print(f"Total components in database: {result['component_count']}")
print(f"Components fetched for grouping: {result['debug_info'].get('raw_component_count', 0)}")
print(f"Location groups created: {result['debug_info'].get('grouped_component_count', 0)}")
print(f"Total pages: {result['total_pages']}")
print(f"Pagination warning: {result['debug_info'].get('pagination_warning', 'None')}")

# Test last page
if result['total_pages'] > 1:
    print(f"\nTesting last page (page {result['total_pages']})...")
    request = factory.get(f'/search/?q=battery&page={result["total_pages"]}&per_page=10&sort_by=newest')
    start = time.time()
    result2 = search_components_service(request, return_data_only=True)
    elapsed = time.time() - start
    
    print(f"Last page search time: {elapsed:.2f}s")
    print(f"Components on last page: {len(result2['page_obj'].object_list) if result2.get('page_obj') else 0}")
    print(f"Error: {result2.get('error', 'None')}")