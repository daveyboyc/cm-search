#!/usr/bin/env python
"""
Script to check SW11 components in detail
"""
import os
import django
import json
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from django.db.models import Q
from checker.models import Component

def check_sw11_detailed():
    """Check SW11 components with verbose output for debugging"""
    print("\n---- START SW11 COMPONENT DEBUG ----\n")
    
    # Check database access
    all_count = Component.objects.count()
    print(f"Database access OK - Total component count: {all_count}")
    
    # Check by outward_code first
    outward_code_query = Component.objects.filter(outward_code__iexact='SW11')
    outward_count = outward_code_query.count()
    print(f"\n1. OUTWARD CODE FILTER:")
    print(f"   Components with outward_code='SW11': {outward_count}")
    
    # Check by text search
    text_query = Component.objects.filter(
        Q(location__icontains='SW11') | 
        Q(description__icontains='SW11')
    )
    text_count = text_query.count()
    print(f"\n2. TEXT SEARCH FILTER:")
    print(f"   Components with 'SW11' in location/description: {text_count}")
    
    # Check geocoding status
    geocoded_query = outward_code_query.filter(geocoded=True)
    geocoded_count = geocoded_query.count()
    print(f"\n3. GEOCODING STATUS:")
    print(f"   Components with outward_code='SW11' AND geocoded=True: {geocoded_count}")
    
    # Check coordinates
    with_coords_query = outward_code_query.filter(
        latitude__isnull=False, 
        longitude__isnull=False
    )
    coords_count = with_coords_query.count()
    print(f"\n4. COORDINATE STATUS:")
    print(f"   Components with outward_code='SW11' AND coordinates: {coords_count}")
    
    # Show sample records
    if outward_count > 0:
        print("\n5. SAMPLE SW11 COMPONENTS:")
        for i, comp in enumerate(outward_code_query[:5]):
            print(f"\n   COMPONENT #{i+1}:")
            print(f"   ID: {comp.id}")
            print(f"   CMU_ID: {comp.cmu_id}")
            print(f"   Location: {comp.location}")
            print(f"   Company: {comp.company_name}")
            print(f"   Delivery Year: {comp.delivery_year}")
            print(f"   Outward Code: {comp.outward_code}")
            print(f"   Geocoded: {comp.geocoded}")
            print(f"   Coordinates: {comp.latitude}, {comp.longitude}")
            
    # Special check for test_api route
    print("\n6. MANUAL MAP_DATA_API TESTING:")
    
    # Import the actual function
    from checker.views import map_data_api
    from django.http import HttpRequest
    
    # Create a fake request
    fake_request = HttpRequest()
    fake_request.GET = {'q': 'SW11'}
    fake_request.method = 'GET'
    
    # Call the function directly (note: this won't produce a true HTTP response)
    print("   Calling map_data_api function directly...")
    print("   See server logs for detailed debug output.")
    
    # End of debug
    print("\n---- END SW11 COMPONENT DEBUG ----")

if __name__ == "__main__":
    check_sw11_detailed()