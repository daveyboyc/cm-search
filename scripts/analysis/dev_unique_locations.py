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
OUTPUT_FILE = 'checker/data/postcodes/test_unique_locations_mapping.json'

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

def process_unique_locations(limit=200):
    """Process a subset of unique locations to extract county information"""
    print(f"Processing up to {limit} unique locations...")
    
    # Get unique locations from components
    unique_locations = Component.objects.values('location').distinct().exclude(
        location__isnull=True).exclude(location='').order_by('?')[:limit]
    
    print(f"Found {len(unique_locations)} unique locations to process")
    
    # Store results
    results = {
        'locations_mapped': 0,
        'locations_with_county': 0,
        'location_mappings': [],
        'metadata': {
            'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'locations_processed': len(unique_locations)
        }
    }
    
    # Process each location
    for loc_dict in tqdm(unique_locations):
        location = loc_dict['location']
        
        # Extract postcodes from location
        full_postcodes, outward_codes = extract_postcodes_from_location(location)
        
        location_info = {
            'location': location,
            'full_postcodes': full_postcodes,
            'outward_codes': outward_codes,
            'county': None,
            'outcode': None,
            'region': None,
            'status': 'no_postcode_found'
        }
        
        # Try to get county from full postcode first
        if full_postcodes:
            postcode_info = get_postcode_info(full_postcodes[0])
            if postcode_info['valid']:
                location_info['county'] = postcode_info.get('county') or postcode_info.get('district')
                location_info['outcode'] = postcode_info.get('outcode')
                location_info['region'] = postcode_info.get('region')
                location_info['status'] = 'county_from_full_postcode'
                results['locations_with_county'] += 1
        
        # If no county found and we have outward codes, try those
        elif outward_codes and not location_info['county']:
            outcode_info = get_outcode_info(outward_codes[0])
            if outcode_info['valid'] and outcode_info.get('admin_district'):
                location_info['county'] = outcode_info['admin_district'][0]
                location_info['outcode'] = outward_codes[0]
                location_info['region'] = outcode_info.get('region')
                location_info['status'] = 'county_from_outcode'
                results['locations_with_county'] += 1
        
        # Add to results if we found anything useful
        if location_info['county'] or location_info['outcode']:
            results['locations_mapped'] += 1
            
        # Add to the detailed mappings
        results['location_mappings'].append(location_info)
    
    # Calculate success rate
    success_rate = (results['locations_with_county'] / len(unique_locations)) * 100 if unique_locations else 0
    results['metadata']['success_rate'] = f"{success_rate:.2f}%"
    
    # Save results to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Total locations processed: {len(unique_locations)}")
    print(f"Locations successfully mapped: {results['locations_mapped']}")
    print(f"Locations with county information: {results['locations_with_county']}")
    print(f"Success rate: {success_rate:.2f}%")
    print(f"\nDetailed results saved to {OUTPUT_FILE}")
    
    return results

if __name__ == "__main__":
    # Process a sample of unique locations (default 200)
    import argparse
    
    parser = argparse.ArgumentParser(description='Process unique locations to extract county information')
    parser.add_argument('--limit', type=int, default=200, help='Number of unique locations to process')
    
    args = parser.parse_args()
    process_unique_locations(limit=args.limit) 