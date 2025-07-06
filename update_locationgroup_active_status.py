#!/usr/bin/env python
"""Update is_active field for all LocationGroups based on auction years."""

import os
import sys
import django
import re

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup
from django.db import transaction

def is_auction_year_active(auction_years):
    """Check if any auction year is 2024 or later."""
    if not auction_years:
        return False
    
    # Handle dict format (auction_years is usually a dict with years as keys)
    if isinstance(auction_years, dict):
        for year_str in auction_years.keys():
            match = re.search(r'(\d{4})', str(year_str))
            if match:
                year = int(match.group(1))
                if year >= 2024:
                    return True
    # Handle list format
    elif isinstance(auction_years, list):
        for year_str in auction_years:
            match = re.search(r'(\d{4})', str(year_str))
            if match:
                year = int(match.group(1))
                if year >= 2024:
                    return True
    
    return False

def update_active_status():
    """Update is_active field for all LocationGroups."""
    print("Updating is_active status for all LocationGroups...")
    
    total = LocationGroup.objects.count()
    updated = 0
    active_count = 0
    
    # Process in batches
    batch_size = 1000
    
    with transaction.atomic():
        for offset in range(0, total, batch_size):
            location_groups = LocationGroup.objects.all()[offset:offset + batch_size]
            
            for lg in location_groups:
                new_status = is_auction_year_active(lg.auction_years)
                if lg.is_active != new_status:
                    lg.is_active = new_status
                    lg.save(update_fields=['is_active'])
                    updated += 1
                
                if new_status:
                    active_count += 1
            
            print(f"Processed {min(offset + batch_size, total)}/{total} LocationGroups...")
    
    print(f"\nUpdate complete!")
    print(f"Total LocationGroups: {total}")
    print(f"Updated: {updated}")
    print(f"Active: {active_count}")
    print(f"Inactive: {total - active_count}")

if __name__ == "__main__":
    update_active_status()