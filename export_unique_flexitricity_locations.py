#!/usr/bin/env python
import os
import sys
import django
import datetime
import re
import csv
import urllib.parse  # Add this for URL encoding

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

def export_unique_flexitricity_locations(output_file=None):
    """
    Export unique locations with their most recent auction information for
    Flexitricity load curtailment/drop components to CSV.
    
    Args:
        output_file: Path to output CSV file. If None, a default filename will be generated.
    
    Returns:
        Path to the exported CSV file.
    """
    # Generate default output filename if not provided
    if not output_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"flexitricity_unique_locations_{timestamp}.csv"
    
    # Get current year for determining active status
    current_year = datetime.datetime.now().year
    
    # Define filters
    company_filter = Q(company_name__icontains='FLEXITRICITY')
    description_filter = Q(description__icontains='load drop') | Q(description__icontains='load curtailment')
    
    # Get unique locations (excluding None)
    components = Component.objects.filter(company_filter) \
                              .filter(description_filter) \
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
    print(f"Found {total_count} unique locations with Flexitricity load curtailment/drop components")
    
    # Set up counters
    active_locations = 0
    inactive_locations = 0
    
    # Prepare CSV data
    csv_data = []
    csv_columns = ['Location', 'Status', 'Most Recent Auction', 'Delivery Year', 'Description', 'Derated Capacity (MW)', 'CMU ID', 'Maps Link']
    
    # For each unique location, get the most recent component
    for norm_loc in unique_norm_locations:
        original_loc = locations_map[norm_loc]
        
        try:
            # Get all components with this location
            latest = None
            try:
                # First try exact match
                latest = Component.objects.filter(company_filter) \
                                    .filter(description_filter) \
                                    .filter(location=original_loc) \
                                    .order_by('-delivery_year') \
                                    .first()
            except Exception:
                # If that fails, try a more flexible match
                similar_locations = Component.objects.filter(company_filter) \
                                                  .filter(description_filter) \
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
            
            # Format derated capacity
            try:
                derated_capacity = float(latest.derated_capacity) if latest.derated_capacity else 'N/A'
            except (ValueError, TypeError):
                derated_capacity = 'N/A'
            
            # Create Google Maps link
            encoded_location = urllib.parse.quote(original_loc)
            maps_link = f"https://www.google.com/maps?q={encoded_location}&t=k"  # t=k for satellite view
            
            # Add to CSV data
            csv_data.append({
                'Location': original_loc,
                'Status': status,
                'Most Recent Auction': latest.auction_name,
                'Delivery Year': latest.delivery_year,
                'Description': latest.description,
                'Derated Capacity (MW)': derated_capacity,
                'CMU ID': latest.cmu_id,
                'Maps Link': maps_link
            })
        except Exception as e:
            print(f"Error processing location '{original_loc}': {e}")
    
    # Write to CSV
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"Successfully exported {len(csv_data)} unique locations to {output_file}")
        print(f"\nSummary:")
        print(f"Total unique locations: {total_count}")
        print(f"Active locations: {active_locations}")
        print(f"Inactive locations: {inactive_locations}")
        
        return output_file
    except Exception as e:
        print(f"Error writing CSV file: {e}")
        return None

if __name__ == "__main__":
    try:
        output_file = export_unique_flexitricity_locations()
        print(f"CSV file saved to: {output_file}")
    except Exception as e:
        print(f"Error: {e}") 