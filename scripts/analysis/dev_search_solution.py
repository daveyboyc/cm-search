import requests
import re

# Base URL for the postcodes.io API
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

def get_outcodes_for_place(place: str) -> set:
    """
    Get postcode outcodes for a place name using the postcodes.io API
    """
    # Call the /places endpoint to search for the place name
    response = requests.get(
        f"{POSTCODES_IO_BASE_URL}/places",
        params={"q": place, "limit": 100},
        timeout=10
    )
    
    if not response.ok:
        print(f"Error looking up place: {response.status_code} - {response.text}")
        return set()
    
    data = response.json().get("result", [])
    
    # Extract outcodes from the response
    outcodes = set()
    for item in data:
        outcode = (item.get("outcode") or item.get("code") or "").upper()
        if outcode:
            outcodes.add(outcode)
            
    return outcodes

def get_outcode_details(outcode: str) -> dict:
    """
    Get details about a specific outcode
    """
    response = requests.get(
        f"{POSTCODES_IO_BASE_URL}/outcodes/{outcode}",
        timeout=10
    )
    
    if not response.ok:
        return {}
    
    return response.json().get("result", {})

def is_location_term(term: str) -> bool:
    """
    Check if a term appears to be a location (city, town, etc.)
    """
    # List of common location indicators
    location_indicators = [
        "london", "manchester", "birmingham", "nottingham", "yorkshire", 
        "battersea", "peckham", "leeds", "bristol", "cambridge", "oxford",
        "sheffield", "newcastle", "liverpool", "glasgow", "edinburgh",
        "cardiff", "belfast", "brighton", "norwich", "plymouth", "exeter"
    ]
    
    return term.lower() in location_indicators

def smart_search_components(search_query: str):
    """
    Smart search function that combines location-based and direct text searches
    
    This handles:
    1. Pure location searches (like "Battersea") - uses postcode.io
    2. Specific searches (like "Nottingham Hospital") - breaks into terms
    3. Hybrid searches - uses location data to enhance ranking
    """
    print(f"\nSmart searching for: '{search_query}'")
    
    # Extract terms from the search query
    terms = search_query.lower().split()
    
    # Check if we have location terms
    location_terms = [term for term in terms if is_location_term(term)]
    other_terms = [term for term in terms if term not in location_terms]
    
    if location_terms and not other_terms:
        # Pure location search (e.g., "Battersea", "Nottingham")
        print(f"Pure location search for: {location_terms}")
        for location in location_terms:
            outcodes = get_outcodes_for_place(location)
            print(f"Found outcodes for {location}: {outcodes}")
            
            # In a real implementation, we would search components by these outcodes
            # components = Component.objects.filter(outward_code__in=outcodes)
            
    elif location_terms and other_terms:
        # Hybrid search (e.g., "Nottingham Hospital", "Battersea Power Station")
        print(f"Hybrid search with location terms: {location_terms} and other terms: {other_terms}")
        
        # First, get outcodes for location terms
        all_outcodes = set()
        for location in location_terms:
            outcodes = get_outcodes_for_place(location)
            all_outcodes.update(outcodes)
            
        print(f"Found outcodes for locations: {all_outcodes}")
        
        # In a real implementation, we would combine:
        # 1. Text search on other_terms
        # 2. Location filter by all_outcodes
        # 3. Apply a ranking that boosts components matching both criteria
        
    else:
        # Direct text search (e.g., "Hospital", "Power Station")
        print(f"Direct text search for: {other_terms}")
        
        # In a real implementation, we would do a direct text search
        # components = Component.objects.filter(text_search_field__icontains=" ".join(other_terms))
    
    print("-" * 50)

# Test various search queries
test_queries = [
    "Battersea",
    "Nottingham",
    "Nottingham Hospital",
    "Battersea Power Station",
    "CHP",
    "Hospital",
    "Power Station"
]

for query in test_queries:
    smart_search_components(query) 