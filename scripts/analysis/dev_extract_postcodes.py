import os
import re
import django
import requests
import json
from collections import Counter

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Count

# Postcode.io API base URL
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

# Regular expressions for UK postcodes
# Full postcode pattern (e.g., "SW1A 1AA")
FULL_POSTCODE_PATTERN = r'[A-Z]{1,2}[0-9][A-Z0-9]?\s[0-9][A-Z]{2}'

# Outward code pattern (e.g., "SW1A" or "M1")
OUTWARD_CODE_PATTERN = r'[A-Z]{1,2}[0-9][A-Z0-9]?'

def extract_postcodes_from_location(location_text):
    """
    Extract UK postcodes from location text.
    Returns both full postcodes and outward codes.
    """
    if not location_text or not isinstance(location_text, str):
        return [], []
    
    # Convert to uppercase for consistent matching
    text = location_text.upper()
    
    # Find full postcodes (with space)
    full_postcodes = re.findall(FULL_POSTCODE_PATTERN, text)
    
    # Find all potential outward codes
    all_outward_codes = re.findall(OUTWARD_CODE_PATTERN, text)
    
    # Filter outward codes to exclude those that are part of full postcodes
    outward_codes = []
    for outward in all_outward_codes:
        # Check if this outward code is part of any full postcode
        if not any(outward in full_pc for full_pc in full_postcodes):
            outward_codes.append(outward)
    
    return full_postcodes, outward_codes

def validate_postcode_with_api(postcode):
    """
    Validate a postcode using the postcodes.io API and return location info
    """
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

def validate_outcode_with_api(outcode):
    """
    Validate an outcode using the postcodes.io API and return location info
    """
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

def analyze_sample_locations(limit=100):
    """
    Analyze a sample of locations from the Component model
    to test postcode extraction
    """
    print(f"Analyzing {limit} sample location records...")
    components = Component.objects.exclude(location__isnull=True).exclude(location='')[:limit]
    
    # Count statistics
    total_analyzed = 0
    locations_with_postcodes = 0
    locations_with_outward_codes = 0
    total_postcodes_found = 0
    total_outward_codes_found = 0
    
    # Collect example results for display
    examples = []
    all_postcodes = []
    all_outward_codes = []
    
    for component in components:
        total_analyzed += 1
        location = component.location
        
        full_postcodes, outward_codes = extract_postcodes_from_location(location)
        
        if full_postcodes:
            locations_with_postcodes += 1
            total_postcodes_found += len(full_postcodes)
            all_postcodes.extend(full_postcodes)
        
        if outward_codes:
            locations_with_outward_codes += 1
            total_outward_codes_found += len(outward_codes)
            all_outward_codes.extend(outward_codes)
        
        # Add interesting examples to our results
        if full_postcodes or outward_codes:
            examples.append({
                'id': component.id,
                'location': location,
                'full_postcodes': full_postcodes,
                'outward_codes': outward_codes
            })
    
    # Print summary statistics
    print("\n=== Extraction Statistics ===")
    print(f"Total locations analyzed: {total_analyzed}")
    print(f"Locations with full postcodes: {locations_with_postcodes} ({locations_with_postcodes/total_analyzed*100:.1f}%)")
    print(f"Locations with outward codes only: {locations_with_outward_codes} ({locations_with_outward_codes/total_analyzed*100:.1f}%)")
    print(f"Total full postcodes found: {total_postcodes_found}")
    print(f"Total outward codes found: {total_outward_codes_found}")
    
    # Show the most common postcodes and outward codes
    print("\n=== Most Common Full Postcodes ===")
    for postcode, count in Counter(all_postcodes).most_common(10):
        print(f"{postcode}: {count} occurrences")
    
    print("\n=== Most Common Outward Codes ===")
    for outcode, count in Counter(all_outward_codes).most_common(10):
        print(f"{outcode}: {count} occurrences")
    
    # Show example extractions
    print("\n=== Example Extractions ===")
    for i, example in enumerate(examples[:10]):  # Show first 10 examples
        print(f"\nExample {i+1}:")
        print(f"Location: {example['location']}")
        print(f"Full postcodes: {example['full_postcodes']}")
        print(f"Outward codes: {example['outward_codes']}")
    
    return all_postcodes, all_outward_codes, examples

def validate_extracted_postcodes(postcodes, limit=5):
    """
    Validate a sample of extracted postcodes using the API
    """
    print("\n=== Validating Sample Postcodes with API ===")
    unique_postcodes = list(set(postcodes))[:limit]  # Validate only a few to avoid rate limiting
    
    for postcode in unique_postcodes:
        print(f"\nValidating full postcode: {postcode}")
        result = validate_postcode_with_api(postcode)
        
        if result['valid']:
            print(f"Valid postcode: {result['postcode']}")
            print(f"Outcode: {result['outcode']}")
            print(f"County: {result['county']}")
            print(f"District: {result['district']}")
            print(f"Region: {result['region']}")
        else:
            print(f"Invalid postcode: {result['error']}")

def validate_extracted_outcodes(outcodes, limit=5):
    """
    Validate a sample of extracted outcodes using the API
    """
    print("\n=== Validating Sample Outcodes with API ===")
    unique_outcodes = list(set(outcodes))[:limit]  # Validate only a few to avoid rate limiting
    
    for outcode in unique_outcodes:
        print(f"\nValidating outcode: {outcode}")
        result = validate_outcode_with_api(outcode)
        
        if result['valid']:
            print(f"Valid outcode: {result['outcode']}")
            print(f"Admin districts: {result['admin_district']}")
            print(f"Region: {result['region']}")
            print(f"Coordinates: {result['longitude']}, {result['latitude']}")
        else:
            print(f"Invalid outcode: {result['error']}")

def get_unique_location_count():
    """Get count of unique location values in database"""
    return Component.objects.exclude(location__isnull=True).exclude(location='').values('location').distinct().count()

if __name__ == "__main__":
    # Print total unique locations
    unique_locations = get_unique_location_count()
    print(f"Total unique locations in database: {unique_locations}")
    
    # Analyze sample locations
    all_postcodes, all_outward_codes, examples = analyze_sample_locations(limit=200)
    
    # Validate a few of the extracted postcodes
    validate_extracted_postcodes(all_postcodes, limit=5)
    
    # Validate a few of the extracted outcodes  
    validate_extracted_outcodes(all_outward_codes, limit=5) 