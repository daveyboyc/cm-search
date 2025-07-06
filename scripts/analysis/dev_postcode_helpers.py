"""
Test script for the postcode_helpers.py module.
This script tests the various postcode helper functions.
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

# Import the functions from the module
from checker.services.postcode_helpers import (
    validate_postcode,
    get_nearest_postcodes,
    get_outcode_details,
    get_area_for_any_postcode,
    outcodes_for_place
)

def test_validate_postcode():
    print("\n=== Testing validate_postcode ===")
    test_cases = [
        "SW1A 1AA",  # Valid: Buckingham Palace
        "NG1 5FT",   # Valid: Nottingham
        "ABC 123",   # Invalid format
        "SW11",      # Incomplete (outcode only)
    ]
    
    for postcode in test_cases:
        is_valid = validate_postcode(postcode)
        print(f"Postcode '{postcode}' is {'valid' if is_valid else 'invalid'}")

def test_outcodes_for_place():
    print("\n=== Testing outcodes_for_place ===")
    test_cases = [
        "Battersea",
        "Nottingham",
        "Peckham",
        "Birmingham",
        "Manchester",
        "London",
    ]
    
    for place in test_cases:
        outcodes = outcodes_for_place(place)
        print(f"Outcodes for '{place}': {outcodes}")

def test_get_nearest_postcodes():
    print("\n=== Testing get_nearest_postcodes ===")
    test_cases = [
        "SW1A 1AA",  # Buckingham Palace
        "NG1 5FT",   # Nottingham
        "SW11",      # Battersea (outcode only)
        "NG1",       # Nottingham (outcode only)
    ]
    
    for postcode in test_cases:
        nearest = get_nearest_postcodes(postcode, limit=3)
        print(f"Nearest to '{postcode}': {nearest}")

def test_get_outcode_details():
    print("\n=== Testing get_outcode_details ===")
    test_cases = [
        "SW11",  # Battersea
        "NG1",   # Nottingham
    ]
    
    for outcode in test_cases:
        details = get_outcode_details(outcode)
        print(f"Details for '{outcode}':")
        print(f"  Admin district: {details.get('admin_district')}")
        print(f"  Parliamentary constituency: {details.get('parliamentary_constituency')}")
        print(f"  Region: {details.get('region')}")

def test_get_area_for_postcode():
    print("\n=== Testing get_area_for_any_postcode ===")
    test_cases = [
        "SW11 1AA",  # Battersea
        "NG1 5FT",   # Nottingham
        "SW1A 1AA",  # Buckingham Palace
    ]
    
    for postcode in test_cases:
        areas = get_area_for_any_postcode(postcode)
        print(f"Areas for '{postcode}': {areas}")

if __name__ == "__main__":
    # Run all the tests
    test_validate_postcode()
    test_outcodes_for_place()
    test_get_nearest_postcodes()
    test_get_outcode_details()
    test_get_area_for_postcode() 