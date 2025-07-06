#!/usr/bin/env python
"""Test script to verify LocationGroups are active."""

import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.services.location_group_check import should_use_location_groups, get_location_groups_stats
from django.core.cache import cache

def main():
    print("=== Testing LocationGroups Status ===\n")
    
    # Clear the cache to get fresh results
    cache_key = 'location_groups_ready'
    cache.delete(cache_key)
    print(f"Cleared cache key: {cache_key}\n")
    
    # Get stats
    stats = get_location_groups_stats()
    if stats:
        print("LocationGroups Statistics:")
        print(f"  - Total location groups: {stats['location_groups']:,}")
        print(f"  - Total components: {stats['total_components']:,}")
        print(f"  - Covered components: {stats['covered_components']:,}")
        print(f"  - Coverage percentage: {stats['coverage_percentage']:.1f}%")
        print(f"  - Is ready (>80% coverage): {stats['is_ready']}\n")
    else:
        print("Failed to get LocationGroups statistics\n")
    
    # Test should_use_location_groups
    result = should_use_location_groups()
    print(f"should_use_location_groups() returned: {result}\n")
    
    # Check if it's now cached
    cached_result = cache.get(cache_key)
    print(f"Cached result: {cached_result}\n")
    
    # Check specific location groups
    from checker.models import LocationGroup
    sample_groups = LocationGroup.objects.order_by('-component_count')[:5]
    
    if sample_groups:
        print("Top 5 LocationGroups by component count:")
        for lg in sample_groups:
            print(f"  - {lg.location}: {lg.component_count} components, {lg.normalized_capacity_mw:.1f} MW")
    else:
        print("No LocationGroups found in database!")

if __name__ == "__main__":
    main()