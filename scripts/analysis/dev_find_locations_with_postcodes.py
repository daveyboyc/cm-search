import os
import re
import django
import json

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Q

# Regular expressions for UK postcodes
# Full postcode pattern (e.g., "SW1A 1AA")
FULL_POSTCODE_PATTERN = r'[A-Z]{1,2}[0-9][A-Z0-9]?\s[0-9][A-Z]{2}'

# Outward code pattern (e.g., "SW1A" or "M1")
OUTWARD_CODE_PATTERN = r'[A-Z]{1,2}[0-9][A-Z0-9]?'

def find_locations_with_postcodes(limit=50):
    """Find locations that likely contain postcodes using regex"""
    print(f"Searching for locations with postcodes...")
    
    # Case-insensitive matching with regex
    # Look for locations with full postcodes first (more reliable)
    full_postcode_locations = Component.objects.filter(
        location__iregex=r'[A-Z]{1,2}[0-9][A-Z0-9]?\s[0-9][A-Z]{2}'
    ).values('location').distinct()[:limit]
    
    print(f"Found {len(full_postcode_locations)} locations with full postcodes")
    
    # Also look for locations with just outward codes
    outward_code_locations = Component.objects.filter(
        ~Q(location__in=[l['location'] for l in full_postcode_locations]),
        location__iregex=r'[A-Z]{1,2}[0-9][A-Z0-9]?'
    ).values('location').distinct()[:limit]
    
    print(f"Found {len(outward_code_locations)} locations with outward codes")
    
    # Show examples
    print("\n=== Locations with Full Postcodes ===")
    for i, loc in enumerate(full_postcode_locations):
        print(f"{i+1}. {loc['location']}")
        
        # Extract postcode
        full_postcodes = re.findall(FULL_POSTCODE_PATTERN, loc['location'].upper())
        if full_postcodes:
            print(f"   Found postcode: {full_postcodes[0]}")
    
    print("\n=== Locations with Outward Codes ===")
    for i, loc in enumerate(outward_code_locations):
        print(f"{i+1}. {loc['location']}")
        
        # Extract outward code
        outward_codes = re.findall(OUTWARD_CODE_PATTERN, loc['location'].upper())
        if outward_codes:
            print(f"   Found outward code: {outward_codes[0]}")
    
    return {
        'full_postcode_locations': [l['location'] for l in full_postcode_locations],
        'outward_code_locations': [l['location'] for l in outward_code_locations]
    }

if __name__ == "__main__":
    # Find locations with postcodes
    locations = find_locations_with_postcodes(limit=50)
    
    # Save results to file for examination
    with open('test_locations_with_postcodes.json', 'w') as f:
        json.dump(locations, f, indent=2)
    
    print(f"\nResults saved to test_locations_with_postcodes.json") 