#!/usr/bin/env python
import os
import sys
import django
import datetime
import csv
import argparse

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

def export_asda_flexitricity_components(output_file=None):
    """
    Export Asda components managed by Flexitricity with load curtailment/drop to CSV,
    including active/inactive status based on delivery year.
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
    
    # Display unique locations count
    unique_locations = set(comp.location for comp in components)
    print(f"Found {len(unique_locations)} unique Asda store locations")
    
    if not total_count:
        print("No components found to export.")
        return
    
    # Prepare data for CSV export
    export_data = []
    
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
        
        export_data.append({
            'location': comp.location,
            'description': comp.description,
            'company_name': comp.company_name,
            'cmu_id': comp.cmu_id,
            'delivery_year': comp.delivery_year,
            'auction_name': comp.auction_name,
            'status': status,
            'derated_capacity': comp.derated_capacity_mw if hasattr(comp, 'derated_capacity_mw') else None,
            'component_id': comp.id
        })
    
    # Determine output filename
    if not output_file:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"asda_flexitricity_components_{timestamp}.csv"
    
    # Export to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # Use the keys from the first data item as fieldnames
        fieldnames = export_data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in export_data:
            writer.writerow(row)
    
    print(f"Exported {len(export_data)} components to {output_file}")
    print(f"Full path: {os.path.abspath(output_file)}")
    
    # Count active vs. inactive for summary
    active_count = sum(1 for item in export_data if item['status'] == 'ACTIVE')
    inactive_count = sum(1 for item in export_data if item['status'] == 'INACTIVE')
    unknown_count = sum(1 for item in export_data if item['status'] == 'UNKNOWN')
    
    print(f"\nSummary:")
    print(f"Active components: {active_count}")
    print(f"Inactive components: {inactive_count}")
    print(f"Unknown status: {unknown_count}")
    
    return export_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export Asda Flexitricity load curtailment components to CSV')
    parser.add_argument('--output', '-o', type=str, help='Output CSV filename')
    args = parser.parse_args()
    
    try:
        export_asda_flexitricity_components(args.output)
    except Exception as e:
        print(f"Error: {e}") 