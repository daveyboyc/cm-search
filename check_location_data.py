import os
import json
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.models import Component

# Check if we have pre-identified locations
if os.path.exists('test_locations_with_postcodes.json'):
    print("Loading pre-identified locations...")
    with open('test_locations_with_postcodes.json', 'r') as f:
        locations_data = json.load(f)
        
    full_postcode_locations = locations_data.get('full_postcode_locations', [])
    outward_code_locations = locations_data.get('outward_code_locations', [])
    
    print(f"Found {len(full_postcode_locations)} locations with full postcodes")
    print(f"Found {len(outward_code_locations)} locations with outward codes")
    print(f"Total: {len(full_postcode_locations) + len(outward_code_locations)} locations")
    
    # Check which ones are already processed
    already_processed = Component.objects.exclude(
        county__isnull=True, outward_code__isnull=True
    ).exclude(
        county='', outward_code=''
    ).values_list('location', flat=True).distinct()
    
    already_processed_set = set(already_processed)
    print(f"Found {len(already_processed_set)} already processed locations")
    
    # How many of our identified locations are already processed?
    full_already_processed = [loc for loc in full_postcode_locations if loc in already_processed_set]
    outward_already_processed = [loc for loc in outward_code_locations if loc in already_processed_set]
    
    print(f"Already processed full postcode locations: {len(full_already_processed)}/{len(full_postcode_locations)}")
    print(f"Already processed outward code locations: {len(outward_already_processed)}/{len(outward_code_locations)}")
    
    # How many are left to process?
    full_to_process = [loc for loc in full_postcode_locations if loc not in already_processed_set]
    outward_to_process = [loc for loc in outward_code_locations if loc not in already_processed_set]
    
    print(f"Full postcode locations to process: {len(full_to_process)}")
    print(f"Outward code locations to process: {len(outward_to_process)}")
    
    # Show examples of locations to process
    if full_to_process:
        print("\nExample full postcode locations to process:")
        for loc in full_to_process[:5]:
            print(f"- {loc}")
    
    if outward_to_process:
        print("\nExample outward code locations to process:")
        for loc in outward_to_process[:5]:
            print(f"- {loc}")
else:
    print("No pre-identified locations file found.") 