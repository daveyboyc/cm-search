#!/usr/bin/env python
"""
Script to check for SW11 components in the database
"""
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from django.db.models import Q
from checker.models import Component

def check_sw11_components():
    """Check for components matching SW11 search query"""
    print("Checking for SW11 components in the database...")
    
    # Direct pattern matching for SW11
    sw11_direct = Component.objects.filter(
        Q(cmu_id__icontains='sw11') |
        Q(company_name__icontains='sw11') |
        Q(location__icontains='sw11') |
        Q(description__icontains='sw11') |
        Q(technology__icontains='sw11')
    )
    
    print(f"Found {sw11_direct.count()} components with direct SW11 match")
    
    # Check outward code separately
    sw11_outward = Component.objects.filter(outward_code='SW11')
    print(f"Found {sw11_outward.count()} components with outward_code='SW11'")
    
    # Check for partial match in location
    sw11_partial = Component.objects.filter(
        Q(location__icontains='sw1') |
        Q(location__icontains='battersea') |  # Battersea is in SW11
        Q(location__icontains='clapham') |    # Parts of Clapham are in SW11
        Q(location__icontains='south west london')
    )
    print(f"Found {sw11_partial.count()} components with potential SW11 area match")
    
    # Display a few sample records
    print("\nSample direct SW11 matches:")
    for comp in sw11_direct[:5]:
        print(f"ID: {comp.id}, CMU: {comp.cmu_id}, Location: {comp.location}, Geocoded: {comp.geocoded}")
        print(f"  Company: {comp.company_name}")
        print(f"  Coordinates: {comp.latitude}, {comp.longitude}")
        print(f"  Outward Code: {comp.outward_code}, County: {comp.county}")
        print("---")
    
    print("\nSample outward code SW11 matches:")
    for comp in sw11_outward[:5]:
        print(f"ID: {comp.id}, CMU: {comp.cmu_id}, Location: {comp.location}, Geocoded: {comp.geocoded}")
        print(f"  Company: {comp.company_name}")
        print(f"  Coordinates: {comp.latitude}, {comp.longitude}")
        print(f"  Outward Code: {comp.outward_code}, County: {comp.county}")
        print("---")
    
    # Check geocoded status for area matches
    geocoded_count = sw11_partial.filter(geocoded=True).count()
    non_geocoded_count = sw11_partial.filter(geocoded=False).count()
    print(f"\nOut of {sw11_partial.count()} potential area matches:")
    print(f"  - {geocoded_count} are geocoded")
    print(f"  - {non_geocoded_count} are not geocoded")
    
    return sw11_direct, sw11_outward, sw11_partial

if __name__ == "__main__":
    check_sw11_components()