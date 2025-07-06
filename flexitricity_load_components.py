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

def extract_flexitricity_load_components():
    """
    Extract all components for Flexitricity with load curtailment/drop related descriptions.
    Uses flexible matching to ensure we find all relevant components.
    """
    print("Searching for Flexitricity load curtailment/drop components...")
    
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
        'demand reduction',
        'demand response',
        'load shifting',
        'DSR'
    ]
    
    # Build company filter
    company_filter = Q()
    for company in company_variations:
        company_filter |= Q(company_name__icontains=company)
    
    # Build description filter
    description_filter = Q()
    for term in description_terms:
        description_filter |= Q(description__icontains=term)
    
    # Query the database
    components = Component.objects.filter(company_filter).filter(description_filter).order_by('location')
    
    count = components.count()
    print(f"Found {count} matching components")
    
    if count == 0:
        print("No matching components found. Checking with broader criteria...")
        
        # Check how many components exist for each company variation
        for company in company_variations:
            count = Component.objects.filter(company_name__icontains=company).count()
            print(f"Components for '{company}': {count}")
        
        # Check descriptions across all companies
        for term in description_terms:
            count = Component.objects.filter(description__icontains=term).count()
            print(f"Components with '{term}' in description: {count}")
        
        # Search for any Asda components as a fallback (mentioned in original query)
        asda_components = Component.objects.filter(
            Q(location__icontains='Asda') | 
            Q(description__icontains='Asda')
        ).filter(description_filter).count()
        print(f"Found {asda_components} Asda components with load curtailment terms")
        
        # Try an even broader search if nothing found
        if Component.objects.filter(company_filter).count() == 0:
            # List all unique company names containing "flex" to see if there's a different spelling
            flex_companies = Component.objects.filter(
                company_name__icontains='flex'
            ).values_list('company_name', flat=True).distinct()
            print(f"Companies containing 'flex': {list(flex_companies)}")
            
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
            'component_id': comp.id,  # Include database ID for reference
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
        filename = f"flexitricity_load_components_{timestamp}.csv"

    # Define the field names based on the first component
    fieldnames = components[0].keys()

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for component in components:
            writer.writerow(component)
    
    print(f"Exported {len(components)} components to {filename}")
    print(f"Full path: {os.path.abspath(filename)}")

def extract_all_flexitricity_components():
    """
    Extract all Flexitricity components regardless of description,
    as a fallback if specific search returns no results.
    """
    print("Extracting ALL Flexitricity components as fallback...")
    
    components = Component.objects.filter(
        Q(company_name__icontains='FLEXITRICITY') |
        Q(company_name__icontains='Flexitricity')
    ).order_by('location')
    
    count = components.count()
    print(f"Found {count} total Flexitricity components")
    
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

if __name__ == "__main__":
    print("Starting export of Flexitricity load components...")
    components = extract_flexitricity_load_components()
    
    # If no specific components found, export all Flexitricity components
    if not components:
        print("No specific components found. Trying to export ALL Flexitricity components...")
        components = extract_all_flexitricity_components()
    
    if components:
        # Use command line argument for filename if provided
        filename = sys.argv[1] if len(sys.argv) > 1 else None
        save_to_csv(components, filename)
    else:
        print("No components to export.") 