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

# Output file path
OUTPUT_FILE = 'checker/data/postcodes/postcode_mapping.json'

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

def get_postcode_info(postcode):
    """
    Get county/region information for a postcode from the API
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

def get_outcode_info(outcode):
    """
    Get county/region information for an outcode from the API
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

def extract_all_postcodes_from_database(batch_size=500):
    """
    Extract all postcodes from the Component model locations
    """
    print("Extracting postcodes from all locations in database...")
    
    # Get total count for progress tracking
    total_components = Component.objects.exclude(location__isnull=True).exclude(location='').count()
    print(f"Total components with locations: {total_components}")
    
    # Process in batches to avoid memory issues
    full_postcodes_set = set()
    outward_codes_set = set()
    processed = 0
    
    # Create batches
    batches = (total_components // batch_size) + 1
    
    for batch in range(batches):
        start = batch * batch_size
        end = start + batch_size
        components = Component.objects.exclude(location__isnull=True).exclude(location='')[start:end]
        
        if not components:
            break
        
        for component in components:
            location = component.location
            full_postcodes, outward_codes = extract_postcodes_from_location(location)
            full_postcodes_set.update(full_postcodes)
            outward_codes_set.update(outward_codes)
            
        processed += len(components)
        print(f"Processed {processed}/{total_components} components...")
    
    # Convert sets to lists
    full_postcodes = list(full_postcodes_set)
    outward_codes = list(outward_codes_set)
    
    print(f"Found {len(full_postcodes)} unique full postcodes")
    print(f"Found {len(outward_codes)} unique outward codes")
    
    return full_postcodes, outward_codes

def build_postcode_mapping(full_postcodes, outward_codes, api_rate_limit=60):
    """
    Build a mapping of postcodes to counties/regions using the API
    """
    print("\nBuilding postcode to county/region mapping...")
    
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
    
    # Process full postcodes
    print("\nProcessing full postcodes...")
    requests_made = 0
    
    for i, postcode in enumerate(tqdm(full_postcodes)):
        # Check rate limit (60 requests per minute for postcodes.io)
        if requests_made >= api_rate_limit:
            print(f"Rate limit reached ({api_rate_limit} requests). Sleeping for 1 minute...")
            time.sleep(60)
            requests_made = 0
        
        info = get_postcode_info(postcode)
        requests_made += 1
        
        if info['valid']:
            outcode = info.get('outcode')
            county = info.get('county') or 'Unknown'
            district = info.get('district') or 'Unknown'
            region = info.get('region') or 'Unknown'
            
            mapping['full_postcodes'][postcode] = {
                'outcode': outcode,
                'county': county,
                'district': district,
                'region': region
            }
            
            # Also update outcode mapping if we have the info
            if outcode:
                # Update outcode to county mapping (if county is available)
                if county != 'Unknown':
                    mapping['outcode_to_county'][outcode] = county
                
                # Update outcode to region mapping
                if region != 'Unknown':
                    mapping['outcode_to_region'][outcode] = region
    
    # Process outward codes
    print("\nProcessing outward codes...")
    requests_made = 0
    
    for i, outcode in enumerate(tqdm(outward_codes)):
        # Check if we already have info for this outcode from full postcodes
        if outcode in mapping['outcode_to_region'] or outcode in mapping['outcode_to_county']:
            continue
            
        # Check rate limit
        if requests_made >= api_rate_limit:
            print(f"Rate limit reached ({api_rate_limit} requests). Sleeping for 1 minute...")
            time.sleep(60)
            requests_made = 0
        
        info = get_outcode_info(outcode)
        requests_made += 1
        
        if info['valid']:
            admin_districts = info.get('admin_district', [])
            region = info.get('region') or 'Unknown'
            
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
    
    # Calculate coverage statistics
    full_postcode_coverage = len(mapping['full_postcodes']) / len(full_postcodes) * 100 if full_postcodes else 0
    outward_code_coverage = len(mapping['outward_codes']) / len(outward_codes) * 100 if outward_codes else 0
    
    mapping['metadata']['full_postcode_coverage'] = f"{full_postcode_coverage:.1f}%"
    mapping['metadata']['outward_code_coverage'] = f"{outward_code_coverage:.1f}%"
    
    return mapping

def save_mapping_to_file(mapping, output_file):
    """
    Save the mapping to a JSON file
    """
    print(f"\nSaving mapping to {output_file}...")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"Mapping saved successfully!")

def build_location_mapping(mapping):
    """
    Build a mapping of locations to outward codes and counties
    """
    print("\nBuilding location mapping...")
    
    location_mapping = defaultdict(lambda: {'outcodes': [], 'counties': []})
    
    # Get unique locations from the database
    locations = Component.objects.exclude(location__isnull=True).exclude(location='') \
                      .values('location').distinct()
    
    for loc_dict in tqdm(locations):
        location = loc_dict['location']
        
        if not location:
            continue
            
        # Extract postcodes from location
        full_postcodes, outward_codes = extract_postcodes_from_location(location)
        
        # Extract location name (usually the first part before a comma or other delimiter)
        parts = re.split(r'[,\n]', location)
        location_name = parts[0].strip().lower() if parts else location.lower()
        
        # Get counties and regions from the postcodes
        counties = set()
        regions = set()
        outcodes = set()
        
        # Process full postcodes
        for pc in full_postcodes:
            pc_info = mapping['full_postcodes'].get(pc, {})
            outcode = pc_info.get('outcode')
            county = pc_info.get('county')
            region = pc_info.get('region')
            
            if outcode:
                outcodes.add(outcode)
            
            if county and county != 'Unknown':
                counties.add(county)
            
            if region and region != 'Unknown':
                regions.add(region)
        
        # Process outward codes
        for oc in outward_codes:
            outcodes.add(oc)
            
            # Get county and region from the mapping
            county = mapping['outcode_to_county'].get(oc)
            region = mapping['outcode_to_region'].get(oc)
            
            if county and county != 'Unknown':
                counties.add(county)
            
            if region and region != 'Unknown':
                regions.add(region)
        
        # Update location mapping
        if location_name:
            location_mapping[location_name]['outcodes'].extend(list(outcodes))
            location_mapping[location_name]['counties'].extend(list(counties))
    
    # Convert defaultdict to regular dict
    result = {
        'locations': dict(location_mapping),
        'metadata': {
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_locations': len(location_mapping)
        }
    }
    
    return result

def save_location_mapping(mapping, output_file):
    """
    Save the location mapping to a JSON file
    """
    location_output_file = output_file.replace('.json', '_locations.json')
    print(f"\nSaving location mapping to {location_output_file}...")
    
    with open(location_output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"Location mapping saved successfully!")

if __name__ == "__main__":
    # Extract all postcodes from the database
    full_postcodes, outward_codes = extract_all_postcodes_from_database(batch_size=1000)
    
    # Build the mapping using the API
    mapping = build_postcode_mapping(full_postcodes, outward_codes)
    
    # Save the mapping to a file
    save_mapping_to_file(mapping, OUTPUT_FILE)
    
    # Build and save location mapping
    location_mapping = build_location_mapping(mapping)
    save_location_mapping(location_mapping, OUTPUT_FILE) 