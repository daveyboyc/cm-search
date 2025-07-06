#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

from django.db.models import Q
from checker.models import Component

def preview_flexitricity_load_components(limit=100):
    """
    Show the first {limit} Flexitricity components with load curtailment/drop.
    """
    print(f"Searching for Flexitricity components with load curtailment/drop (limit: {limit})...")
    
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
    
    # Query the database
    components = Component.objects.filter(company_filter).filter(description_filter).order_by('location')
    
    total_count = components.count()
    print(f"Found {total_count} total matching components")
    
    # Get limited results
    limited_components = components[:limit]
    print(f"Showing first {len(limited_components)} components:")
    
    # Preview the data
    print("\n" + "="*80)
    print(f"{'LOCATION':<40} | {'DESCRIPTION':<80}")
    print("="*80)
    
    for i, comp in enumerate(limited_components, 1):
        # Truncate description if needed
        desc = comp.description if comp.description else "N/A"
        if len(desc) > 77:
            desc = desc[:77] + "..."
        
        loc = comp.location if comp.location else "N/A"
        if len(loc) > 37:
            loc = loc[:37] + "..."
            
        print(f"{i:3}. {loc:<37} | {desc}")
    
    print("="*80)
    print(f"Displayed {len(limited_components)} of {total_count} total components")
    
    # Ask if the user wants to see locations with 'Asda' specifically
    asda_components = []
    for comp in components:
        if 'asda' in (comp.location or '').lower() or 'asda' in (comp.description or '').lower():
            asda_components.append(comp)
    
    if asda_components:
        print(f"\nFound {len(asda_components)} Asda-specific components out of {total_count} total.")
        show_asda = input("Would you like to see only the Asda locations? (y/n): ").lower().strip()
        
        if show_asda == 'y':
            print("\n" + "="*80)
            print("ASDA LOCATIONS ONLY")
            print("="*80)
            print(f"{'LOCATION':<40} | {'DESCRIPTION':<80}")
            print("-"*80)
            
            for i, comp in enumerate(asda_components, 1):
                desc = comp.description if comp.description else "N/A"
                if len(desc) > 77:
                    desc = desc[:77] + "..."
                
                loc = comp.location if comp.location else "N/A"
                if len(loc) > 37:
                    loc = loc[:37] + "..."
                    
                print(f"{i:3}. {loc:<37} | {desc}")
            
            print("="*80)
            print(f"Displayed {len(asda_components)} Asda components")
    
    return total_count, limited_components

if __name__ == "__main__":
    try:
        preview_flexitricity_load_components()
    except KeyboardInterrupt:
        print("\nPreview canceled by user.")
    except Exception as e:
        print(f"Error: {e}") 