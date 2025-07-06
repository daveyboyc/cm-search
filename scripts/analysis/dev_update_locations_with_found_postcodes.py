import os
import re
import django
import json
import requests
import time
from collections import defaultdict

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component
from django.db.models import Count, F

# Postcode.io API base URL
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

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

def test_update_found_postcode_locations():
    """Test updating locations that we know contain postcodes"""
    print("Loading test locations with postcodes...")
    
    try:
        with open('test_locations_with_postcodes.json', 'r') as f:
            locations_data = json.load(f)
            
        full_postcode_locations = locations_data.get('full_postcode_locations', [])
        outward_code_locations = locations_data.get('outward_code_locations', [])
        
        print(f"Loaded {len(full_postcode_locations)} full postcode locations")
        print(f"Loaded {len(outward_code_locations)} outward code locations")
        
        # Create a combined list
        test_locations = full_postcode_locations + outward_code_locations
        print(f"Testing with {len(test_locations)} total locations")
        
        # Create mapping
        location_mapping = {}
        success_count = 0
        county_count = 0
        
        for location in test_locations:
            full_postcodes, outward_codes = extract_postcodes_from_location(location)
            
            location_info = {
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
                    
                    if location_info['county']:
                        county_count += 1
                        
                    success_count += 1
            
            # If no county found and we have outward codes, try those
            elif outward_codes and not location_info['county']:
                outcode_info = get_outcode_info(outward_codes[0])
                if outcode_info['valid'] and outcode_info.get('admin_district'):
                    location_info['county'] = outcode_info['admin_district'][0]
                    location_info['outcode'] = outward_codes[0]
                    location_info['region'] = outcode_info.get('region')
                    location_info['status'] = 'county_from_outcode'
                    
                    if location_info['county']:
                        county_count += 1
                        
                    success_count += 1
            
            # Add to mapping
            location_mapping[location] = location_info
            
            # Add a small delay to avoid rate limits
            time.sleep(0.2)
        
        # Print results
        print(f"\n=== Mapping Results ===")
        print(f"Total locations processed: {len(test_locations)}")
        print(f"Successfully mapped: {success_count}")
        print(f"Locations with county info: {county_count}")
        
        # Now update a few example components
        print(f"\n=== Testing Component Updates ===")
        
        update_count = 0
        for location, mapping in location_mapping.items():
            if mapping['county'] or mapping['outcode']:
                # Get a sample component with this location
                component = Component.objects.filter(location=location).first()
                
                if component:
                    print(f"Updating component ID {component.id} with location: {location}")
                    print(f"  County: {mapping['county']}")
                    print(f"  Outward code: {mapping['outcode']}")
                    
                    # Update the component
                    component.county = mapping['county']
                    component.outward_code = mapping['outcode']
                    component.save()
                    
                    update_count += 1
                    
                    # Verify the update
                    updated_component = Component.objects.get(id=component.id)
                    print(f"  Verified: county={updated_component.county}, outward_code={updated_component.outward_code}")
                    
                    # Only update 5 components as a test
                    if update_count >= 5:
                        break
        
        print(f"\nSuccessfully updated {update_count} test components")
        return location_mapping
        
    except Exception as e:
        print(f"Error: {e}")
        return {}

if __name__ == "__main__":
    # Run the test
    mapping = test_update_found_postcode_locations()
    
    # Save mapping for examination
    with open('test_postcode_update_results.json', 'w') as f:
        json.dump(mapping, f, indent=2)
        
    print(f"\nResults saved to test_postcode_update_results.json") 