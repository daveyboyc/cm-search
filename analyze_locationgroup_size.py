#!/usr/bin/env python3
"""
Analyze LocationGroup record sizes and propose optimization
"""
import os
import sys
import django
import json
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup

def analyze_locationgroup_sizes():
    """Analyze the size of LocationGroup JSON fields"""
    
    # Get a sample of LocationGroups
    sample_groups = LocationGroup.objects.all()[:10]
    
    print("=== LocationGroup Size Analysis ===\n")
    
    total_sizes = {
        'cmu_ids': 0,
        'descriptions': 0,
        'auction_years': 0,
        'technologies': 0,
        'companies': 0,
        'total': 0
    }
    
    for lg in sample_groups:
        print(f"\nLocation: {lg.location}")
        print(f"Component count: {lg.component_count}")
        
        # Calculate sizes of JSON fields
        cmu_ids_size = len(json.dumps(lg.cmu_ids))
        descriptions_size = len(json.dumps(lg.descriptions))
        auction_years_size = len(json.dumps(lg.auction_years))
        technologies_size = len(json.dumps(lg.technologies))
        companies_size = len(json.dumps(lg.companies))
        
        total_size = cmu_ids_size + descriptions_size + auction_years_size + technologies_size + companies_size
        
        print(f"  CMU IDs: {len(lg.cmu_ids)} items, {cmu_ids_size} bytes")
        print(f"  Descriptions: {len(lg.descriptions)} items, {descriptions_size} bytes")
        print(f"  Auction Years: {len(lg.auction_years)} items, {auction_years_size} bytes")
        print(f"  Technologies: {len(lg.technologies)} items, {technologies_size} bytes")
        print(f"  Companies: {len(lg.companies)} items, {companies_size} bytes")
        print(f"  TOTAL JSON SIZE: {total_size} bytes ({total_size/1024:.2f} KB)")
        
        total_sizes['cmu_ids'] += cmu_ids_size
        total_sizes['descriptions'] += descriptions_size
        total_sizes['auction_years'] += auction_years_size
        total_sizes['technologies'] += technologies_size
        total_sizes['companies'] += companies_size
        total_sizes['total'] += total_size
    
    # Calculate averages
    print("\n=== Average Sizes (10 records) ===")
    for field, size in total_sizes.items():
        avg_size = size / 10
        print(f"{field}: {avg_size:.0f} bytes ({avg_size/1024:.2f} KB)")
    
    # Check what queries are actually using these fields
    print("\n=== Field Usage Analysis ===")
    print("Checking which fields are actually needed for different views...")
    
    # Get total count
    total_count = LocationGroup.objects.count()
    print(f"\nTotal LocationGroup records: {total_count}")
    
    # Estimate total egress
    avg_record_size_kb = total_sizes['total'] / 10 / 1024
    total_potential_egress_mb = (total_count * avg_record_size_kb) / 1024
    print(f"Estimated total egress if all records fetched: {total_potential_egress_mb:.2f} MB")
    
    print("\n=== OPTIMIZATION RECOMMENDATIONS ===")
    print("1. Use defer() to exclude large JSON fields when not needed")
    print("2. Create separate summary fields with just counts")
    print("3. Move detailed lists to a separate related model")
    print("4. Use select_related/prefetch_related instead of storing denormalized data")
    print("5. Consider using PostgreSQL array fields instead of JSON for lists")

def check_query_patterns():
    """Check how LocationGroup is queried in the codebase"""
    print("\n=== Query Pattern Analysis ===")
    
    # Simulate a search query to see what fields are accessed
    from checker.services.location_search import search_locationgroups
    
    # Test with a small query
    results = search_locationgroups("battery")[:5]
    
    print("\nFields accessed in search results:")
    if results:
        lg = results[0]
        # Try to access different fields and see which ones are used
        print(f"- location: {lg.location}")
        print(f"- component_count: {lg.component_count}")
        print(f"- is_active: {lg.is_active}")
        print(f"- normalized_capacity_mw: {lg.normalized_capacity_mw}")
        
        # Check if JSON fields are accessed
        print("\nJSON fields accessed:")
        print(f"- technologies: {len(lg.technologies)} items")
        print(f"- companies: {len(lg.companies)} items")
        # Note: descriptions, cmu_ids, auction_years might not be needed for search

if __name__ == "__main__":
    analyze_locationgroup_sizes()
    check_query_patterns()