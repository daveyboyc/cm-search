#!/usr/bin/env python
import os
import sys
import django
import datetime
import re
import urllib.parse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')

try:
    django.setup()
except ImportError as e:
    print(f"Error setting up Django: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

from django.db.models import Q, Max
from checker.models import Component

def normalize_location(location):
    """Normalize location to help with deduplication."""
    if not location:
        return ""
    
    # Convert to lowercase
    loc = location.lower()
    
    # Remove quotes
    loc = loc.replace('"', '').replace("'", "")
    
    # Remove common separators and standardize whitespace
    loc = re.sub(r'[,\-\/\\]', ' ', loc)
    loc = re.sub(r'\s+', ' ', loc).strip()
    
    # Remove common words that don't add value for matching
    loc = re.sub(r'\b(and|the|ltd|limited)\b', '', loc)
    
    return loc

def show_city_energy_locations_excel_format():
    """
    Display ALL unique locations for CITY ENERGY MANAGEMENT SERVICES LIMITED
    in a tab-separated format that can be copied into Excel.
    """
    # Get current year for determining active status
    current_year = datetime.datetime.now().year
    
    # Define filters - looking for CITY ENERGY MANAGEMENT SERVICES LIMITED
    company_filter = Q(company_name__icontains='CITY ENERGY MANAGEMENT SERVICES LIMITED')
    
    # Get unique locations (excluding None)
    components = Component.objects.filter(company_filter) \
                              .exclude(location__isnull=True) \
                              .exclude(location='')
    
    # Group by normalized location to truly deduplicate
    locations_map = {}  # Map normalized location to original location
    for comp in components:
        if not comp.location:
            continue
        
        norm_loc = normalize_location(comp.location)
        if norm_loc and norm_loc not in locations_map:
            locations_map[norm_loc] = comp.location
    
    # Get sorted list of unique normalized locations
    unique_norm_locations = sorted(locations_map.keys())
    
    total_count = len(unique_norm_locations)
    print(f"Found {total_count} unique locations for CITY ENERGY MANAGEMENT SERVICES LIMITED")
    print("Format: Tab-separated values (copy and paste into Excel)")
    print("\n" + "="*100)
    
    # Print Excel-friendly header (tab-separated)
    print("Location\tStatus\tDelivery Year\tAuction\tDescription\tCMU ID\tGoogle Maps URL")
    
    # Set up counters
    active_locations = 0
    inactive_locations = 0
    
    # For each unique location, get the most recent component
    for norm_loc in unique_norm_locations:
        original_loc = locations_map[norm_loc]
        
        try:
            # Get all components with this location
            latest = None
            try:
                # First try exact match
                latest = Component.objects.filter(company_filter) \
                                    .filter(location=original_loc) \
                                    .order_by('-delivery_year') \
                                    .first()
            except Exception:
                # If that fails, try a more flexible match
                similar_locations = Component.objects.filter(company_filter) \
                                                  .filter(location__icontains=norm_loc.split()[0]) \
                                                  .order_by('-delivery_year')
                
                if similar_locations.exists():
                    latest = similar_locations.first()
            
            if not latest or not latest.delivery_year or not latest.delivery_year.isdigit():
                continue
            
            # Determine active status
            try:
                year = int(latest.delivery_year)
                if year >= current_year:
                    status = 'ACTIVE'
                    active_locations += 1
                else:
                    status = 'INACTIVE'
                    inactive_locations += 1
            except (ValueError, TypeError):
                status = 'UNKNOWN'
            
            # Get description
            description = latest.description if latest.description else "N/A"
            
            # Create Google Maps link
            encoded_location = urllib.parse.quote(original_loc)
            maps_url = f"https://www.google.com/maps?q={encoded_location}&t=k"
            
            # Print as tab-separated line for Excel
            # Make sure to handle any tabs in the text fields
            location_excel = original_loc.replace('\t', ' ')
            description_excel = description.replace('\t', ' ')
            auction_excel = latest.auction_name.replace('\t', ' ') if latest.auction_name else "N/A"
            
            print(f"{location_excel}\t{status}\t{latest.delivery_year}\t{auction_excel}\t{description_excel}\t{latest.cmu_id}\t{maps_url}")
            
        except Exception as e:
            # Skip quietly if there's an error
            pass
    
    print("="*100)
    
    # Display summary
    print(f"\nSummary:")
    print(f"Total unique locations: {total_count}")
    print(f"Active locations: {active_locations}")
    print(f"Inactive locations: {inactive_locations}")
    
    return unique_norm_locations

if __name__ == "__main__":
    try:
        show_city_energy_locations_excel_format()
    except Exception as e:
        print(f"Error: {e}") 