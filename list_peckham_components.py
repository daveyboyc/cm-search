import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q

def list_peckham_components():
    search_term = "peckham"
    
    # Traditional search (only using location field)
    traditional_filter = Q(location__icontains=search_term)
    traditional_results = Component.objects.filter(traditional_filter).distinct()
    
    # Enhanced search (using location, county, and outward_code)
    enhanced_filter = traditional_filter | Q(outward_code="SE15")
    enhanced_results = Component.objects.filter(enhanced_filter).distinct()
    
    # Get the IDs that are only in enhanced results (not in traditional)
    traditional_ids = set(traditional_results.values_list('id', flat=True))
    enhanced_only_ids = set(enhanced_results.values_list('id', flat=True)) - traditional_ids
    enhanced_only_results = Component.objects.filter(id__in=enhanced_only_ids)
    
    # Print traditional search results
    print("\n=== Traditional Search Results (location contains 'peckham') ===")
    print(f"Total results: {traditional_results.count()}")
    for i, result in enumerate(traditional_results):
        print(f"{i+1}. [{result.id}] {result.location}")
        if result.company_name:
            print(f"   Company: {result.company_name}")
        if hasattr(result, 'county') and result.county:
            print(f"   County: {result.county}")
        if hasattr(result, 'outward_code') and result.outward_code:
            print(f"   Outward code: {result.outward_code}")
        print()
    
    # Print enhanced-only search results (not found in traditional)
    print("\n=== Additional Results from Enhanced Search (SE15 outward code) ===")
    print(f"Total additional results: {enhanced_only_results.count()}")
    for i, result in enumerate(enhanced_only_results):
        print(f"{i+1}. [{result.id}] {result.location}")
        if result.company_name:
            print(f"   Company: {result.company_name}")
        if hasattr(result, 'county') and result.county:
            print(f"   County: {result.county}")
        if hasattr(result, 'outward_code') and result.outward_code:
            print(f"   Outward code: {result.outward_code}")
        print()

if __name__ == "__main__":
    list_peckham_components() 