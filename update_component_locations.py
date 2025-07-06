import os
import re
import django
import requests
import json
import time
from collections import defaultdict
from tqdm import tqdm
from django.db.models import Count, Case, When, F, Q

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component

# Postcode.io API base URL
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

# Output file path for the mapping
MAPPING_FILE = 'checker/data/postcodes/location_county_mapping.json'

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

def create_location_mapping(limit=0):
    """Create a mapping of all unique locations to counties and outcodes
    
    Args:
        limit: Optional limit on the number of locations to process (for testing)
    """
    print("Getting all unique locations from the database...")
    
    # Check if mapping file exists already and load it
    previous_mapping = {}
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r') as f:
                prev_data = json.load(f)
                previous_mapping = prev_data.get('mapping', {})
                print(f"Loaded {len(previous_mapping)} previously mapped locations")
        except Exception as e:
            print(f"Error loading previous mapping: {e}")
    
    # First, get locations that already have county or outward_code set
    # so we can skip them to avoid duplicate processing
    already_processed = set()
    processed_components = Component.objects.exclude(
        county__isnull=True, outward_code__isnull=True
    ).exclude(
        county='', outward_code=''
    ).values_list('location', flat=True).distinct()
    
    already_processed.update(processed_components)
    print(f"Found {len(already_processed)} locations already processed in the database")
    
    # Check if we have pre-identified locations with postcodes
    if os.path.exists('test_locations_with_postcodes.json'):
        print("Loading pre-identified locations with postcodes...")
        try:
            with open('test_locations_with_postcodes.json', 'r') as f:
                locations_data = json.load(f)
                
            full_postcode_locations = locations_data.get('full_postcode_locations', [])
            outward_code_locations = locations_data.get('outward_code_locations', [])
            
            # Filter out already processed locations
            full_postcode_locations = [loc for loc in full_postcode_locations if loc not in already_processed]
            outward_code_locations = [loc for loc in outward_code_locations if loc not in already_processed]
            
            print(f"Found {len(full_postcode_locations)} locations with full postcodes")
            print(f"Found {len(outward_code_locations)} locations with outward codes")
            
            # Create priority-ordered list
            all_locations = []
            
            # Process full postcodes first
            all_locations.extend(full_postcode_locations)
            
            # Then process outward codes
            all_locations.extend(outward_code_locations)
            
            total_locations = len(all_locations)
            
            # Apply limit if provided (for testing)
            if limit > 0:
                print(f"TEST MODE: Limiting to {limit} locations")
                unique_locations = all_locations[:limit]
                total_locations = len(unique_locations)
            else:
                unique_locations = all_locations
            
            print(f"Processing {total_locations} unique locations with postcodes")
        except Exception as e:
            print(f"Error loading pre-identified locations: {e}")
            # Fall back to normal approach
            unique_locations = Component.objects.values('location').distinct().exclude(
                location__in=already_processed
            ).exclude(
                location__isnull=True
            ).exclude(
                location=''
            )
            
            if limit > 0:
                unique_locations = list(unique_locations[:limit])
                total_locations = len(unique_locations)
            else:
                total_locations = unique_locations.count()
                
            print(f"Falling back to generic approach, found {total_locations} locations")
    else:
        # Fall back to general approach if no pre-identified locations
        unique_locations = Component.objects.values('location').distinct().exclude(
            location__in=already_processed
        ).exclude(
            location__isnull=True
        ).exclude(
            location=''
        )
        
        if limit > 0:
            unique_locations = list(unique_locations[:limit])
            total_locations = len(unique_locations)
        else:
            total_locations = unique_locations.count()
            
        print(f"Using generic approach, found {total_locations} locations")
    
    # Store mapping
    location_mapping = previous_mapping.copy()
    
    # Track progress
    processed = 0
    mapped = 0
    with_county = 0
    skipped_no_postcode = 0
    
    # Process in batches to avoid API rate limits
    batch_size = 100
    
    # Convert to list for slicing if a query
    if hasattr(unique_locations, 'all'):
        location_list = list(unique_locations)
    else:
        location_list = unique_locations
        
    total_batches = (len(location_list) + batch_size - 1) // batch_size
    
    for i in range(0, len(location_list), batch_size):
        batch = location_list[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} of {total_batches} ({i}-{min(i+batch_size, len(location_list))})")
        
        batch_locations = []
        for loc_dict in batch:
            # Extract location string from dict if needed
            if isinstance(loc_dict, dict):
                location = loc_dict.get('location', '')
            else:
                location = loc_dict
                
            batch_locations.append(location)
            
            # Skip if already in the mapping
            if location in location_mapping:
                continue
                
            processed += 1
            
            # Extract postcodes from location
            full_postcodes, outward_codes = extract_postcodes_from_location(location)
            
            # Skip if no postcodes found
            if not full_postcodes and not outward_codes:
                skipped_no_postcode += 1
                location_mapping[location] = {
                    'county': None,
                    'outcode': None,
                    'region': None,
                    'status': 'no_postcode_found'
                }
                continue
            
            county = None
            outcode = None
            region = None
            status = 'no_data_found'
            
            # Try to get county from full postcode first
            if full_postcodes:
                postcode_info = get_postcode_info(full_postcodes[0])
                if postcode_info['valid']:
                    county = postcode_info.get('county') or postcode_info.get('district')
                    outcode = postcode_info.get('outcode')
                    region = postcode_info.get('region')
                    status = 'county_from_full_postcode'
                    with_county += 1
            
            # If no county found and we have outward codes, try those
            elif outward_codes and not county:
                outcode_info = get_outcode_info(outward_codes[0])
                if outcode_info['valid'] and outcode_info.get('admin_district'):
                    county = outcode_info['admin_district'][0]
                    outcode = outward_codes[0]
                    region = outcode_info.get('region')
                    status = 'county_from_outcode'
                    with_county += 1
            
            # Add to mapping
            location_mapping[location] = {
                'county': county,
                'outcode': outcode,
                'region': region,
                'status': status
            }
            
            if county or outcode:
                mapped += 1
        
        # Save progress after each batch
        print(f"Progress: {processed}/{total_locations} locations processed ({mapped} with county/outcode, {skipped_no_postcode} skipped - no postcode)")
        
        # Save mapping to file after each batch to preserve progress
        mapping_data = {
            'mapping': location_mapping,
            'metadata': {
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_locations': total_locations,
                'locations_processed': processed,
                'locations_mapped': mapped,
                'locations_with_county': with_county,
                'locations_skipped_no_postcode': skipped_no_postcode,
                'progress_percentage': f"{(processed / total_locations * 100) if total_locations else 0:.2f}%"
            }
        }
        
        os.makedirs(os.path.dirname(MAPPING_FILE), exist_ok=True)
        with open(MAPPING_FILE, 'w') as f:
            json.dump(mapping_data, f, indent=2)
        
        # Add small delay to avoid API rate limits
        time.sleep(1)
    
    # Calculate overall success rate
    success_rate = (with_county / (total_locations - skipped_no_postcode)) * 100 if (total_locations - skipped_no_postcode) > 0 else 0
    
    # Save final mapping to file
    mapping_data = {
        'mapping': location_mapping,
        'metadata': {
            'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_locations': total_locations,
            'locations_processed': processed,
            'locations_mapped': mapped,
            'locations_with_county': with_county,
            'locations_skipped_no_postcode': skipped_no_postcode,
            'success_rate': f"{success_rate:.2f}%"
        }
    }
    
    os.makedirs(os.path.dirname(MAPPING_FILE), exist_ok=True)
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping_data, f, indent=2)
    
    print(f"\n=== Summary ===")
    print(f"Total locations to process: {total_locations}")
    print(f"Locations already processed previously: {len(previous_mapping)}")
    print(f"Locations processed this run: {processed}")
    print(f"Locations skipped (no postcode): {skipped_no_postcode}")
    print(f"Locations successfully mapped: {mapped}")
    print(f"Locations with county information: {with_county}")
    print(f"Success rate: {success_rate:.2f}%")
    print(f"\nMapping saved to {MAPPING_FILE}")
    
    return mapping_data

def update_components_from_mapping(mapping_file=MAPPING_FILE):
    """Update all components using the location mapping"""
    print(f"Loading location mapping from {mapping_file}...")
    
    # Load the mapping file
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    location_mapping = mapping_data['mapping']
    total_mapped_locations = len(location_mapping)
    
    print(f"Found {total_mapped_locations} mapped locations")
    
    # Get stats on what's already updated
    already_updated = Component.objects.exclude(
        county__isnull=True, outward_code__isnull=True
    ).exclude(
        county='', outward_code=''
    ).count()
    
    total_components = Component.objects.count()
    print(f"Already updated: {already_updated} out of {total_components} components ({already_updated/total_components*100:.2f}%)")
    
    # Track progress
    updated_components = 0
    skipped_components = 0
    
    # Update components in batches
    batch_size = 1000
    
    print(f"Updating components in batches of {batch_size}...")
    
    # For better performance, process locations in batches
    # This avoids having to loop through all locations for each component
    location_batches = []
    batch = []
    count = 0
    
    # Only include locations that have useful data (county or outcode)
    locations_with_data = {
        loc: data for loc, data in location_mapping.items() 
        if data.get('county') or data.get('outcode')
    }
    
    print(f"Found {len(locations_with_data)} locations with useful county/outcode data")
    
    for location in locations_with_data:
        batch.append(location)
        count += 1
        if count % batch_size == 0:
            location_batches.append(batch)
            batch = []
    
    if batch:  # Add remaining locations
        location_batches.append(batch)
    
    # Process each batch of locations
    total_batches = len(location_batches)
    print(f"Processing {total_batches} batches of locations")
    
    for i, loc_batch in enumerate(location_batches):
        print(f"Processing batch {i+1}/{total_batches}")
        
        # Get components for this batch of locations
        components_batch = Component.objects.filter(location__in=loc_batch)
        
        # Use a single query with case statements for better performance
        case_county = Case(
            *[When(location=loc, then=models.Value(locations_with_data[loc]['county']))
              for loc in loc_batch if locations_with_data[loc]['county']],
            default=F('county')
        )
        
        case_outcode = Case(
            *[When(location=loc, then=models.Value(locations_with_data[loc]['outcode']))
              for loc in loc_batch if locations_with_data[loc]['outcode']],
            default=F('outward_code')
        )
        
        # Update in bulk
        batch_updated = components_batch.update(
            county=case_county,
            outward_code=case_outcode
        )
        
        updated_components += batch_updated
        
        # Print progress
        print(f"Batch {i+1}/{total_batches} complete. Updated {batch_updated} components.")
        print(f"Total progress: {updated_components} updated ({updated_components/(total_components-already_updated)*100:.2f}% of remaining)")
        
        # Add a small delay to reduce database load
        time.sleep(0.5)
    
    # Final stats
    print(f"\n=== Update Summary ===")
    print(f"Total components updated: {updated_components}")
    print(f"Components skipped (already had data): {already_updated}")
    
    # Get stats on county and outward_code coverage
    with_county = Component.objects.exclude(county__isnull=True).exclude(county='').count()
    with_outcode = Component.objects.exclude(outward_code__isnull=True).exclude(outward_code='').count()
    
    print(f"Components with county: {with_county}/{total_components} ({with_county/total_components*100:.2f}%)")
    print(f"Components with outward_code: {with_outcode}/{total_components} ({with_outcode/total_components*100:.2f}%)")
    
    return updated_components

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create location mapping and update components')
    parser.add_argument('--create-mapping', action='store_true', help='Create the location mapping file')
    parser.add_argument('--update-components', action='store_true', help='Update components using the mapping file')
    parser.add_argument('--mapping-file', type=str, default=MAPPING_FILE, help='Path to mapping file (default: %(default)s)')
    parser.add_argument('--all', action='store_true', help='Do both create mapping and update components')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of locations to process (for testing, 0=no limit)')
    
    args = parser.parse_args()
    
    # Default behavior if no args specified
    if not (args.create_mapping or args.update_components or args.all):
        args.all = True
    
    # Create mapping
    if args.create_mapping or args.all:
        print("=== Creating Location Mapping ===")
        mapping_data = create_location_mapping(limit=args.limit)
    
    # Update components
    if args.update_components or args.all:
        print("\n=== Updating Components ===")
        updated = update_components_from_mapping(args.mapping_file) 