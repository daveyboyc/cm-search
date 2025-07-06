import os
import re
import django
import requests
import json
import time
from collections import defaultdict
from tqdm import tqdm

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Count

# Postcode.io API base URL
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

# Test output file path
OUTPUT_FILE = 'checker/data/postcodes/test_postcode_mapping.json'

# Regular expressions for UK postcodes
# Full postcode pattern (e.g., "SW1A 1AA")
FULL_POSTCODE_PATTERN = r'[A-Z]{1,2}[0-9][A-Z0-9]?\s[0-9][A-Z]{2}'

# Outward code pattern (e.g., "SW1A" or "M1")
OUTWARD_CODE_PATTERN = r'[A-Z]{1,2}[0-9][A-Z0-9]?'

def extract_postcodes_from_location(location_text):
    """Extract UK postcodes from location text"""
    if not location_text or not isinstance(location_text, str):
        return [], []
    
    # Convert to uppercase for consistent matching
    text = location_text.upper()
    
    # Find full postcodes
    full_postcodes = re.findall(FULL_POSTCODE_PATTERN, text)
    
    # Find all outward codes
    all_outward_codes = re.findall(OUTWARD_CODE_PATTERN, text)
    
    # Filter outward codes to exclude those in full postcodes
    outward_codes = []
    for outward in all_outward_codes:
        if not any(outward in full_pc for full_pc in full_postcodes):
            outward_codes.append(outward)
    
    return full_postcodes, outward_codes

def get_postcode_info(postcode):
    """Get information for a postcode using the API"""
    url = f"{POSTCODES_IO_BASE_URL}/postcodes/{postcode}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            return {
                'valid': True,
                'postcode': result.get('postcode'),
                'outcode': result.get('outcode'),
                'county': result.get('admin_county'),
                'district': result.get('admin_district'),
                'region': result.get('region')
            }
        else:
            return {'valid': False, 'error': f"API returned {response.status_code}"}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def get_outcode_info(outcode):
    """Get information for an outcode using the API"""
    url = f"{POSTCODES_IO_BASE_URL}/outcodes/{outcode}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            return {
                'valid': True,
                'outcode': outcode,
                'admin_district': result.get('admin_district', []),
                'region': result.get('region'),
                'longitude': result.get('longitude'),
                'latitude': result.get('latitude')
            }
        else:
            return {'valid': False, 'error': f"API returned {response.status_code}"}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def test_postcode_mapping(limit=50):
    """Test building a postcode mapping with a small sample"""
    print(f"Testing postcode mapping with {limit} random components...")
    
    # Get a random sample of components with location data
    components = Component.objects.exclude(location__isnull=True).exclude(location='').order_by('?')[:limit]
    
    full_postcodes_set = set()
    outward_codes_set = set()
    example_locations = []
    
    # Extract postcodes from locations
    for component in components:
        location = component.location
        full_postcodes, outward_codes = extract_postcodes_from_location(location)
        
        if full_postcodes or outward_codes:
            example_locations.append({
                'id': component.id,
                'location': location,
                'full_postcodes': full_postcodes,
                'outward_codes': outward_codes
            })
            
        full_postcodes_set.update(full_postcodes)
        outward_codes_set.update(outward_codes)
    
    # Convert sets to lists
    full_postcodes = list(full_postcodes_set)
    outward_codes = list(outward_codes_set)
    
    print(f"Found {len(full_postcodes)} unique full postcodes")
    print(f"Found {len(outward_codes)} unique outward codes")
    
    # Show example locations
    print("\n=== Example Locations ===")
    for i, example in enumerate(example_locations[:5]):
        print(f"\nExample {i+1}: {example['location']}")
        print(f"Full postcodes: {example['full_postcodes']}")
        print(f"Outward codes: {example['outward_codes']}")
    
    # Build mapping (with a small sample)
    mapping = {
        'full_postcodes': {},
        'outward_codes': {},
        'outcode_to_county': {},
        'outcode_to_region': {},
        'metadata': {
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_full_postcodes': len(full_postcodes),
            'total_outward_codes': len(outward_codes)
        }
    }
    
    # Process a subset of full postcodes - increased from 10 to 25
    print("\n=== Processing Full Postcodes ===")
    for postcode in full_postcodes[:25]:  # Process 25 for better testing
        print(f"Processing postcode: {postcode}")
        info = get_postcode_info(postcode)
        
        if info['valid']:
            outcode = info.get('outcode')
            county = info.get('county') or 'Unknown'
            district = info.get('district') or 'Unknown'
            region = info.get('region') or 'Unknown'
            
            print(f"- Outcode: {outcode}")
            print(f"- County: {county}")
            print(f"- District: {district}")
            print(f"- Region: {region}")
            
            mapping['full_postcodes'][postcode] = {
                'outcode': outcode,
                'county': county,
                'district': district,
                'region': region
            }
            
            # Update outcode mappings
            if outcode:
                if county != 'Unknown':
                    mapping['outcode_to_county'][outcode] = county
                
                if region != 'Unknown':
                    mapping['outcode_to_region'][outcode] = region
    
    # Process a subset of outward codes - increased from 10 to 25
    print("\n=== Processing Outward Codes ===")
    for outcode in outward_codes[:25]:  # Process 25 for better testing
        # Skip if already in the mapping
        if outcode in mapping['outcode_to_region'] or outcode in mapping['outcode_to_county']:
            print(f"Skipping outcode {outcode} (already processed)")
            continue
            
        print(f"Processing outcode: {outcode}")
        info = get_outcode_info(outcode)
        
        if info['valid']:
            admin_districts = info.get('admin_district', [])
            region = info.get('region') or 'Unknown'
            
            print(f"- Admin districts: {admin_districts}")
            print(f"- Region: {region}")
            
            mapping['outward_codes'][outcode] = {
                'admin_districts': admin_districts,
                'region': region
            }
            
            # Update outcode to county/region mapping
            if admin_districts:
                # Use the first district as the county (approximation)
                mapping['outcode_to_county'][outcode] = admin_districts[0]
            
            if region != 'Unknown':
                mapping['outcode_to_region'][outcode] = region
    
    # Print the resulting mapping
    print("\n=== Final Mapping ===")
    print(f"Full postcodes mapped: {len(mapping['full_postcodes'])}")
    print(f"Outward codes mapped: {len(mapping['outward_codes'])}")
    print(f"Outcode to county mappings: {len(mapping['outcode_to_county'])}")
    print(f"Outcode to region mappings: {len(mapping['outcode_to_region'])}")
    
    # Save mapping to file for inspection
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\nMapping saved to {OUTPUT_FILE}")
    
    return mapping

if __name__ == "__main__":
    # Test with 500 components
    test_postcode_mapping(limit=500) 