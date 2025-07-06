#!/usr/bin/env python
"""
Script to directly test the map_data_api function with minimal HTTP machinery
"""
import os
import django
import json
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

# Create a fully mocked request with proper GET parameters and path
from django.http import HttpRequest
from checker.views import map_data_api

def test_api_directly(query_param="SW11"):
    """Test the map_data_api function directly"""
    print(f"\n----- DIRECT MAP API TEST FOR '{query_param}' -----\n")
    
    # Create a fake request with all the properties needed
    fake_request = HttpRequest()
    fake_request.GET = {'q': query_param}
    fake_request.path = '/api/map-data/'
    fake_request.method = 'GET'
    
    # Call the function directly
    print(f"Calling map_data_api with q='{query_param}'...")
    response = map_data_api(fake_request)
    
    # Get the response content
    content = response.content.decode('utf-8')
    try:
        data = json.loads(content)
        
        # Print summary of response
        print(f"\nResponse contains {len(data.get('features', []))} features")
        print(f"Metadata: {json.dumps(data.get('metadata', {}))}")
        
        # If we got features, print sample
        if data.get('features'):
            first_feature = data['features'][0]
            print(f"\nSample feature:")
            if 'geometry' in first_feature:
                coords = first_feature['geometry'].get('coordinates', [])
                print(f"Coordinates: {coords}")
            
            if 'properties' in first_feature:
                props = first_feature['properties']
                print(f"Title: {props.get('title', 'Unknown')}")
                print(f"Company: {props.get('company', 'Unknown')}")
                print(f"Technology: {props.get('technology', 'Unknown')}")
        else:
            print("\nNo features found in response!")
            
        # Determine why we might not be getting results
        if not data.get('features'):
            print("\nPOSSIBLE ISSUES:")
            print("1. Cache might be returning stale data")
            print("2. Filtering logic might be excluding all components")
            print("3. Features might be empty due to coordinate issues")
            print("4. API might not be connecting to correct database")
        
    except json.JSONDecodeError:
        print("ERROR: Failed to parse JSON response")
        print(f"Response content: {content[:200]}...")
    
    print(f"\n----- END MAP API TEST -----\n")
    
if __name__ == "__main__":
    # Test with SW11
    test_api_directly("SW11")
    
    # Also test with another postcode for comparison
    test_api_directly("E1")