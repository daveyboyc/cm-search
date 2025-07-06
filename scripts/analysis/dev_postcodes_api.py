import requests
import json
import time

def get_outcodes_for_area(area_name):
    """Get outcodes associated with an area by using reverse geocoding"""
    # Approximate coordinates for areas
    area_coordinates = {
        "streatham": {"latitude": 51.4256, "longitude": -0.1272},
        "london": {"latitude": 51.5074, "longitude": -0.1278},
        "manchester": {"latitude": 53.4808, "longitude": -2.2426},
        "battersea": {"latitude": 51.4791, "longitude": -0.1748},
        "peckham": {"latitude": 51.4743, "longitude": -0.0684},
        "nottingham": {"latitude": 52.9548, "longitude": -1.1581},
        "elephant": {"latitude": 51.4937, "longitude": -0.1001},  # Added Elephant and Castle
    }
    
    if area_name.lower() not in area_coordinates:
        print(f"No coordinates found for {area_name}")
        return []
    
    coords = area_coordinates[area_name.lower()]
    
    # Use reverse geocoding to find nearby postcodes
    response = requests.post(
        "https://api.postcodes.io/postcodes",
        json={"geolocations": [coords]}
    )
    
    if response.status_code != 200:
        print(f"API error: {response.status_code}")
        return []
    
    results = response.json()["result"][0]["result"]
    
    # Extract outcodes
    outcodes = set()
    for result in results:
        outcodes.add(result["outcode"])
    
    # Get neighboring outcodes
    all_outcodes = set(outcodes)
    for outcode in outcodes:
        try:
            neighbors_response = requests.get(f"https://api.postcodes.io/outcodes/{outcode}/nearest")
            if neighbors_response.status_code == 200:
                for neighbor in neighbors_response.json()["result"]:
                    all_outcodes.add(neighbor["outcode"])
        except Exception as e:
            print(f"Error getting neighbors for {outcode}: {e}")
    
    return list(all_outcodes)

def get_places_by_name(place_name):
    """
    Get places matching the place name using the postcodes.io API
    """
    print(f"Searching for place: {place_name}")
    
    response = requests.get(
        "https://api.postcodes.io/places",
        params={"q": place_name, "limit": 100}
    )
    
    if response.status_code != 200:
        print(f"API error: {response.status_code}")
        return []
    
    return response.json()["result"]

def get_outcodes_for_postcode(postcode):
    """Get outcode for a postcode and its neighboring outcodes"""
    # First try to get the outcode directly
    outcode = postcode.split()[0] if " " in postcode else postcode
    
    try:
        # Validate the outcode
        response = requests.get(f"https://api.postcodes.io/outcodes/{outcode}")
        if response.status_code != 200:
            print(f"Invalid outcode: {outcode}")
            return []
        
        # Get neighboring outcodes
        neighbors_response = requests.get(f"https://api.postcodes.io/outcodes/{outcode}/nearest")
        if neighbors_response.status_code != 200:
            print(f"Error getting neighbors for {outcode}")
            return [outcode]
        
        outcodes = [outcode]
        for neighbor in neighbors_response.json()["result"]:
            outcodes.append(neighbor["outcode"])
        
        return outcodes
    except Exception as e:
        print(f"Error processing outcode {outcode}: {e}")
        return []

def search_components_using_api_postcodes(location, use_api=True):
    """
    Simulate the search logic using API postcodes instead of hardcoded ones
    """
    start_time = time.time()
    print(f"Searching for components with location: {location}")
    
    # Start with basic location filter
    print(f"Starting with basic filter for: {location}")
    
    related_postcodes = []
    
    if use_api:
        # Check if location is an area name and get related postcodes via API
        outcodes = get_outcodes_for_area(location)
        if outcodes:
            related_postcodes = outcodes
            print(f"API: Found {len(related_postcodes)} related outcodes for area: {location}")
            print(f"Outcodes: {related_postcodes}")
        else:
            # Check if location might be a postcode and get related areas
            outcodes = get_outcodes_for_postcode(location)
            if outcodes:
                related_postcodes = outcodes
                print(f"API: Found {len(related_postcodes)} related outcodes for postcode: {location}")
                print(f"Outcodes: {related_postcodes}")
    else:
        # Use hardcoded values for comparison
        hardcoded = {
            "streatham": ["SW16", "SW17", "CR4"],
            "london": ["SW", "SE", "W", "E", "N", "NW", "EC", "WC"],
            "battersea": ["SW11", "SW8"],
            "peckham": ["SE15", "SE5"],
            "nottingham": ["NG1", "NG2", "NG3", "NG4", "NG5", "NG6", "NG7", "NG8", "NG9"],
            "elephant": ["SE1", "SE17"]  # Added for Elephant and Castle
        }
        
        location_lower = location.lower()
        if location_lower in hardcoded:
            related_postcodes = hardcoded[location_lower]
            print(f"Hardcoded: Found {len(related_postcodes)} related postcodes for: {location}")
            print(f"Postcodes: {related_postcodes}")
    
    end_time = time.time()
    print(f"Search completed in {end_time - start_time:.2f} seconds")
    return related_postcodes

def get_places_data_for_location(location):
    """Get detailed place data for a location using the places API"""
    print(f"\n=== Getting place data for {location} ===")
    places = get_places_by_name(location)
    
    if not places:
        print(f"No place data found for {location}")
        return
    
    print(f"Found {len(places)} places matching '{location}':")
    for place in places:
        print(f"- {place.get('name', 'Unknown')} ({place.get('outcode', 'No outcode')})")
        print(f"  Region: {place.get('region', 'Unknown')}")
        print(f"  Country: {place.get('country', 'Unknown')}")
        if 'longitude' in place and 'latitude' in place:
            print(f"  Coordinates: {place['latitude']}, {place['longitude']}")
        print()

def analyze_search_terms(term1, term2, combined_term):
    """Analyze how search terms are processed to debug AND vs. exact match issues"""
    print(f"\n{'='*80}")
    print(f"ANALYZING SEARCH TERMS")
    print(f"{'='*80}")
    
    print(f"Term 1: '{term1}'")
    print(f"Term 2: '{term2}'")
    print(f"Combined: '{combined_term}'")
    
    # Mock how the search logic would process these terms
    print("\nSimulating search query construction:")
    
    # This is similar to how the search query is constructed in the actual code
    term1_query = f"location__icontains='{term1}' OR description__icontains='{term1}' OR technology__icontains='{term1}'"
    term2_query = f"location__icontains='{term2}' OR description__icontains='{term2}' OR technology__icontains='{term2}'"
    combined_query = f"location__icontains='{combined_term}' OR description__icontains='{combined_term}' OR technology__icontains='{combined_term}'"
    
    print(f"\nQuery for term1 '{term1}':")
    print(term1_query)
    
    print(f"\nQuery for term2 '{term2}':")
    print(term2_query)
    
    print(f"\nQuery for combined '{combined_term}':")
    print(combined_query)
    
    print("\nProblem: The combined query is looking for the exact phrase, not components matching both terms separately")
    print("Solution would be to change the query logic to something like:")
    print(f"(location__icontains='{term1}' OR description__icontains='{term1}') AND (location__icontains='{term2}' OR description__icontains='{term2}')")

# Test locations including "elephant" specific tests
locations_to_test = ["elephant", "elephant and castle"]

for location in locations_to_test:
    print(f"\n{'='*80}")
    print(f"TESTING LOCATION: {location.upper()}")
    print(f"{'='*80}")
    
    # Get place data
    get_places_data_for_location(location)
    
    # Test with API
    print(f"\n=== Testing {location} using API ===")
    api_results = search_components_using_api_postcodes(location, use_api=True)
    
    # Test with hardcoded values
    print(f"\n=== Testing {location} using hardcoded values ===")
    hardcoded_results = search_components_using_api_postcodes(location, use_api=False)
    
    # Compare results
    print(f"\n=== Comparison for {location} ===")
    print(f"API results: {len(api_results)} outcodes")
    print(f"Hardcoded results: {len(hardcoded_results)} postcodes")
    
    # Show differences
    api_set = set(api_results)
    hardcoded_set = set(hardcoded_results)
    
    print(f"Outcodes in API but not hardcoded: {api_set - hardcoded_set}")
    print(f"Outcodes in hardcoded but not API: {hardcoded_set - api_set}")
    print(f"Common outcodes: {api_set.intersection(hardcoded_set)}")

# Analyze the search term issue
analyze_search_terms("elephant", "chp", "elephant chp")
