#!/usr/bin/env python
import os
import sys
import django
import csv
from datetime import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

from django.db.models import Q
from checker.models import Component

def extract_asda_load_components():
    """
    Extract all components related to Asda stores with load curtailment/reduction.
    """
    print("Searching for Asda load curtailment components...")
    
    # Build filter for Asda-related components
    asda_filter = (
        Q(location__icontains='Asda') | 
        Q(description__icontains='Asda') |
        Q(description__icontains='ASDA')
    )
    
    # Build filter for load curtailment-related descriptions
    description_filter = (
        Q(description__icontains='load drop') |
        Q(description__icontains='load curtailment') |
        Q(description__icontains='load reduction') |
        Q(description__icontains='demand reduction') |
        Q(description__icontains='demand response') |
        Q(description__icontains='DSR')
    )
    
    # Query the database for Asda components with load curtailment
    components = Component.objects.filter(asda_filter).filter(description_filter).order_by('location')
    
    count = components.count()
    print(f"Found {count} Asda components with load curtailment")
    
    if count == 0:
        print("No matching components found. Checking with broader criteria...")
        
        # Try just Asda components
        asda_only_count = Component.objects.filter(asda_filter).count()
        print(f"Total Asda components: {asda_only_count}")
        
        # Try specific company search
        for company in ['FLEXITRICITY LIMITED', 'OCTOPUS ENERGY LIMITED']:
            asda_count = Component.objects.filter(asda_filter).filter(company_name__icontains=company).count()
            print(f"Asda components for {company}: {asda_count}")
        
        # Try to find all components with load curtailment terms
        curtailment_count = Component.objects.filter(description_filter).count()
        print(f"Total components with load curtailment terms: {curtailment_count}")
        
        # Return empty list
        return []
    
    result = []
    for comp in components:
        result.append({
            'location': comp.location,
            'description': comp.description,
            'cmu_id': comp.cmu_id,
            'company_name': comp.company_name,
            'delivery_year': comp.delivery_year,
            'auction_name': comp.auction_name,
            'derated_capacity': comp.derated_capacity_mw if hasattr(comp, 'derated_capacity_mw') else None,
            'type': comp.type,
            'technology': comp.technology,
            'component_id': comp.id,
            'status': comp.status if hasattr(comp, 'status') else None,
        })
    
    return result

def extract_all_asda_components():
    """
    Extract all Asda-related components regardless of description,
    as a fallback if specific search returns no results.
    """
    print("Extracting ALL Asda components as fallback...")
    
    asda_filter = (
        Q(location__icontains='Asda') | 
        Q(description__icontains='Asda') |
        Q(description__icontains='ASDA')
    )
    
    components = Component.objects.filter(asda_filter).order_by('location')
    
    count = components.count()
    print(f"Found {count} total Asda components")
    
    if count == 0:
        return []
    
    result = []
    for comp in components:
        result.append({
            'location': comp.location,
            'description': comp.description,
            'cmu_id': comp.cmu_id,
            'company_name': comp.company_name,
            'delivery_year': comp.delivery_year,
            'auction_name': comp.auction_name,
            'derated_capacity': comp.derated_capacity_mw if hasattr(comp, 'derated_capacity_mw') else None,
            'type': comp.type,
            'technology': comp.technology,
            'component_id': comp.id,
            'status': comp.status if hasattr(comp, 'status') else None,
        })
    
    return result

def save_to_csv(components, filename=None):
    """
    Save the components to a CSV file.
    """
    if not components:
        print("No components to export.")
        return

    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"asda_load_components_{timestamp}.csv"

    # Define the field names based on the first component
    fieldnames = components[0].keys()

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for component in components:
            writer.writerow(component)
    
    print(f"Exported {len(components)} components to {filename}")
    print(f"Full path: {os.path.abspath(filename)}")

if __name__ == "__main__":
    print("Starting export of Asda load curtailment components...")
    components = extract_asda_load_components()
    
    # If no specific components found, export all Asda components
    if not components:
        print("No specific components found. Trying to export ALL Asda components...")
        components = extract_all_asda_components()
    
    if components:
        # Use command line argument for filename if provided
        filename = sys.argv[1] if len(sys.argv) > 1 else None
        save_to_csv(components, filename)
    else:
        print("No components to export.") 