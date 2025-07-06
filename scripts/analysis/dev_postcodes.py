import requests
import json
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cmr.settings")
django.setup()

# Now import Django models after setup
from checker.models import Component
from django.db.models import Q

# Base URL for the postcodes.io API
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

def get_outcodes_for_place(place: str) -> set:
    """
    Get postcode outcodes for a place name using the postcodes.io API
    """
    print(f"Searching for place: {place}")
    
    # Call the /places endpoint to search for the place name
    response = requests.get(
        f"{POSTCODES_IO_BASE_URL}/places",
        params={"q": place, "limit": 100},
        timeout=10
    )
    
    if not response.ok:
        print(f"Error: {response.status_code} - {response.text}")
        return set()
    
    data = response.json().get("result", [])
    print(f"Found {len(data)} results")
    
    # Extract outcodes from the response
    outcodes = set()
    for item in data:
        # Try both "outcode" and "code" fields as mentioned in the feedback
        outcode = (item.get("outcode") or item.get("code") or "").upper()
        if outcode:
            outcodes.add(outcode)
            
    return outcodes

def get_nearby_postcodes(postcode: str, limit: int = 10) -> list:
    """
    Get nearby postcodes for a given postcode
    """
    print(f"Finding nearby postcodes for: {postcode}")
    
    # Clean the postcode
    postcode_clean = postcode.upper().replace(" ", "")
    
    # Try to use the /nearest endpoint
    response = requests.get(
        f"{POSTCODES_IO_BASE_URL}/postcodes/{postcode_clean}/nearest",
        params={"limit": limit},
        timeout=10
    )
    
    if not response.ok:
        print(f"Error: {response.status_code} - {response.text}")
        return []
    
    data = response.json().get("result", [])
    return [item.get("postcode") for item in data]

def get_outcode_details(outcode: str) -> dict:
    """
    Get details about a specific outcode
    """
    print(f"Getting details for outcode: {outcode}")
    
    response = requests.get(
        f"{POSTCODES_IO_BASE_URL}/outcodes/{outcode}",
        timeout=10
    )
    
    if not response.ok:
        print(f"Error: {response.status_code} - {response.text}")
        return {}
    
    return response.json().get("result", {})

def get_administrative_area_for_outcode(outcode: str) -> list:
    """
    Get the administrative area(s) for a given outcode
    """
    details = get_outcode_details(outcode)
    return details.get("admin_district", [])

def get_components_by_county_outcode(county: str = None, outcode: str = None, limit: int = 10) -> list:
    """
    Get components by county, outcode, or both
    Uses the new county and outward_code fields
    """
    query = Component.objects.all()
    
    if county:
        query = query.filter(county__icontains=county)
    
    if outcode:
        query = query.filter(outward_code__iexact=outcode)
    
    return list(query[:limit])

def search_components_with_relevance(query: str, limit: int = 20) -> list:
    """
    Search components with relevance ranking for location searches
    
    Priority levels:
    1. Highest (3.0): Components with query directly in location
    2. High (2.0): Components with query in county field
    3. Medium (1.0): Components with matching outward_code
    4. Low (0.1): All other matching components
    """
    # Create the base filter for all potential matches
    component_filter = (
        Q(location__icontains=query)      |
        Q(county__icontains=query)        |   # catches "Nottingham" via county name
        Q(outward_code__iexact=query)     |   # exact NG17 / NG18 etc.
        Q(description__icontains=query)   |
        Q(technology__icontains=query)    |
        Q(company_name__icontains=query)  |
        Q(cmu_id__icontains=query)
    )
    
    # Get all matching components
    matching_components = Component.objects.filter(component_filter)[:500]  # Limiting to 500 for performance
    
    # Create a list to store components with relevance scores
    scored_components = []
    
    for component in matching_components:
        # Default low relevance
        relevance_score = 0.1
        
        # Check for matches in each field and assign relevance
        location = (component.location or "").lower()
        county = (component.county or "").lower()
        outward = (component.outward_code or "").lower()
        
        if query.lower() in location:
            # Highest priority - direct location match
            relevance_score = 3.0
        elif query.lower() in county:
            # High priority - county match
            relevance_score = 2.0
        elif query.lower() == outward:
            # Medium priority - outward code match
            relevance_score = 1.0
        
        # Add component with its score
        scored_components.append({
            "component": component,
            "relevance_score": relevance_score
        })
    
    # Sort by relevance score (highest first)
    scored_components.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # Return limited results
    return scored_components[:limit]

# Main testing function
def run_tests():
    # Test with a few place names
    print("==== Testing basic place names ====")
    places_to_test = ["Battersea", "Peckham", "Nottingham", "Birmingham", "Manchester"]

    for place in places_to_test:
        outcodes = get_outcodes_for_place(place)
        print(f"Outcodes for {place}: {outcodes}")
        print("-" * 50)

    # Test more specific searches
    print("\n==== Testing specific place names (landmark + location) ====")
    specific_places = ["Nottingham Hospital", "Battersea Power Station", "University of Nottingham"]
    for place in specific_places:
        outcodes = get_outcodes_for_place(place)
        print(f"Outcodes for {place}: {outcodes}")
        print("-" * 50)

    # Test county/region searches
    print("\n==== Testing counties/regions ====")
    counties = ["London", "Yorkshire", "Lancashire", "Nottinghamshire"]
    for county in counties:
        outcodes = get_outcodes_for_place(county)
        print(f"Outcodes for {county}: {outcodes}")
        print("-" * 50)

    # Test component searches for counties
    print("\n==== Testing Component searches by county ====")
    counties_to_test = ["Nottinghamshire", "London", "Yorkshire"]
    for county in counties_to_test:
        print(f"\nSearching for components in county: {county}")
        components = get_components_by_county_outcode(county=county, limit=5)
        print(f"Found {len(components)} components. First 5:")
        for component in components:
            print(f"- {component.location} (ID: {component.id})")
        print("-" * 50)

    # Test component searches for postcodes
    print("\n==== Testing Component searches by outcode ====")
    outcodes_to_test = ["NG1", "SW1", "M1", "B1"]
    for outcode in outcodes_to_test:
        print(f"\nSearching for components with outcode: {outcode}")
        components = get_components_by_county_outcode(outcode=outcode, limit=5)
        print(f"Found {len(components)} components. First 5:")
        for component in components:
            print(f"- {component.location} (ID: {component.id})")
        print("-" * 50)

    # Test the relevance-based search
    print("\n==== Testing Relevance-based component search ====")
    location_queries = ["Nottingham", "London", "Manchester"]
    for query in location_queries:
        print(f"\nRelevance search for: {query}")
        scored_results = search_components_with_relevance(query, limit=10)
        print(f"Found {len(scored_results)} results with relevance scores:")
        for idx, result in enumerate(scored_results):
            component = result["component"]
            score = result["relevance_score"]
            print(f"{idx+1}. [{score:.1f}] {component.location} (County: {component.county}, Outcode: {component.outward_code})")
        print("-" * 50)

if __name__ == "__main__":
    run_tests() 