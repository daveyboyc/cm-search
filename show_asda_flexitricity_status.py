#!/usr/bin/env python
import os
import sys
import django
import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')

try:
    django.setup()
except ImportError as e:
    print(f"Error setting up Django: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

from django.db.models import Q
from checker.models import Component

def show_asda_flexitricity_components():
    """
    Display Asda components managed by Flexitricity with load curtailment/drop,
    showing active/inactive status based on delivery year.
    """
    # Get current year for determining active status
    current_year = datetime.datetime.now().year
    
    # Define possible company name variations
    company_variations = [
        'FLEXITRICITY LIMITED', 
        'Flexitricity Limited',
        'Flexitricity',
        'FLEXITRICITY'
    ]
    
    # Define possible description terms
    description_terms = [
        'load drop',
        'load curtailment',
        'load reduction',
        'demand reduction'
    ]
    
    # Build company filter
    company_filter = Q()
    for company in company_variations:
        company_filter |= Q(company_name__icontains=company)
    
    # Build description filter
    description_filter = Q()
    for term in description_terms:
        description_filter |= Q(description__icontains=term)
    
    # Build Asda filter
    asda_filter = Q(location__icontains='Asda') | Q(description__icontains='Asda')
    
    # Query the database
    components = Component.objects.filter(company_filter).filter(description_filter).filter(asda_filter).order_by('location')
    
    total_count = components.count()
    print(f"Found {total_count} Asda components with Flexitricity and load curtailment")
    
    # Display unique locations with status
    unique_locations = set()
    for comp in components:
        unique_locations.add(comp.location)
    print(f"Found {len(unique_locations)} unique Asda store locations")
    
    # Display the data
    print("\n" + "="*100)
    print(f"{'LOCATION':<40} | {'DELIVERY YEAR':<12} | {'STATUS':<10} | {'DESCRIPTION':<40}")
    print("="*100)
    
    for comp in components:
        # Determine active status
        try:
            year = int(comp.delivery_year)
            if year >= current_year:
                status = 'ACTIVE'
            else:
                status = 'INACTIVE'
        except (ValueError, TypeError):
            status = 'UNKNOWN'
        
        # Format description
        desc = comp.description if comp.description else "N/A"
        if len(desc) > 37:
            desc = desc[:37] + "..."
        
        # Format location
        loc = comp.location if comp.location else "N/A"
        if len(loc) > 37:
            loc = loc[:37] + "..."
        
        # Print the row
        print(f"{loc:<40} | {comp.delivery_year or 'N/A':<12} | {status:<10} | {desc}")
    
    print("="*100)
    
    # Count active vs. inactive
    active_count = 0
    inactive_count = 0
    unknown_count = 0
    active_locations = set()
    inactive_locations = set()
    
    for comp in components:
        try:
            year = int(comp.delivery_year)
            if year >= current_year:
                active_count += 1
                active_locations.add(comp.location)
            else:
                inactive_count += 1
                inactive_locations.add(comp.location)
        except (ValueError, TypeError):
            unknown_count += 1
    
    print(f"\nActive components: {active_count}")
    print(f"Inactive components: {inactive_count}")
    print(f"Unknown status: {unknown_count}")
    print(f"Active unique locations: {len(active_locations)}")
    print(f"Inactive unique locations: {len(inactive_locations)}")
    
    # Show common locations
    common_locations = active_locations.intersection(inactive_locations)
    if common_locations:
        print(f"\nLocations with both active and inactive components ({len(common_locations)}):")
        for loc in sorted(common_locations):
            print(f"- {loc}")
    
    return components

if __name__ == "__main__":
    try:
        show_asda_flexitricity_components()
    except Exception as e:
        print(f"Error: {e}") 