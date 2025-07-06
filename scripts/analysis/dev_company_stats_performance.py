#!/usr/bin/env python
import os
import sys
import django
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.test import RequestFactory
from checker.views import company_component_count_list_view

# Create a mock request
factory = RequestFactory()

print("Testing company statistics page performance...")
print("=" * 60)

# Test page 1 (cache miss)
request = factory.get('/companies/by-component-count/')
start = time.time()
response = company_component_count_list_view(request)
elapsed1 = time.time() - start

print(f"\nFirst load (cache miss): {elapsed1:.3f}s")

# Test page 1 again (cache hit)
request = factory.get('/companies/by-component-count/')
start = time.time()
response = company_component_count_list_view(request)
elapsed2 = time.time() - start

print(f"Second load (cache hit): {elapsed2:.3f}s")
print(f"Speedup: {elapsed1/elapsed2:.1f}x")

# Check that auction links are included
if hasattr(response, 'content'):
    content = response.content.decode('utf-8')
    if 'auction-link' in content:
        print("\n✅ Auction links are being displayed!")
        # Count how many
        link_count = content.count('auction-link')
        print(f"Found {link_count} auction links on the page")
    else:
        print("\n❌ No auction links found in the output")

print("\nBenefits of pre-built company links:")
print("1. No dynamic link building during page load")
print("2. Links are stored in database, not built on each request")
print("3. Updates only when data changes (weekly/auction updates)")
print("4. Works perfectly with existing cache system")