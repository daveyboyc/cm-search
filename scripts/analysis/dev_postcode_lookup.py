import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

from checker.services.postcode_lookup import (
    get_outcodes_for_location,
    get_county_for_outcode,
    get_locations_by_county,
    get_all_data_for_location
)

from django.db.models import Q
from checker.models import Component

def test_location_lookup():
    """Test looking up outcodes for locations"""
    print("==== Testing Location Lookup ====")
    
    locations = ["nottingham", "london", "manchester", "peckham", "battersea"]
    
    for location in locations:
        outcodes = get_outcodes_for_location(location)
        print(f"Outcodes for {location}: {outcodes}")
        
        # Get all data
        all_data = get_all_data_for_location(location)
        counties = all_data.get("counties", [])
        print(f"Counties: {counties}")
        print("-" * 50)

def test_outcode_lookup():
    """Test looking up counties for outcodes"""
    print("\n==== Testing Outcode Lookup ====")
    
    outcodes = ["NG1", "NG7", "SW11", "M1", "B1", "SE15"]
    
    for outcode in outcodes:
        county = get_county_for_outcode(outcode)
        print(f"County for {outcode}: {county}")
        print("-" * 50)

def test_county_lookup():
    """Test looking up locations in counties"""
    print("\n==== Testing County Lookup ====")
    
    counties = ["Nottinghamshire", "London", "Greater Manchester"]
    
    for county in counties:
        locations = get_locations_by_county(county)
        print(f"Locations in {county}: {locations}")
        print("-" * 50)

def test_component_search():
    """Test searching components using location data without relying on new fields"""
    print("\n==== Testing Component Search with Location Lookup ====")
    
    locations = ["nottingham", "london", "manchester"]
    
    for location in locations:
        print(f"\nSearching for components in {location}...")
        
        # Get outcodes for this location
        outcodes = get_outcodes_for_location(location)
        print(f"Found {len(outcodes)} outcodes for {location}: {outcodes}")
        
        # Get related counties
        all_data = get_all_data_for_location(location)
        counties = all_data.get("counties", [])
        print(f"Related counties: {counties}")
        
        # Build search filter - only using location since our DB might not have the new fields yet
        location_filter = Q(location__icontains=location)
        
        # Add postcode searches using icontains on location
        postcode_filter = Q()
        for outcode in outcodes:
            postcode_filter |= Q(location__icontains=outcode)
            
        # Combine filters with OR
        combined_filter = location_filter | postcode_filter
        
        # Search components
        components = Component.objects.filter(combined_filter)[:5]
        component_count = Component.objects.filter(combined_filter).count()
        
        print(f"Found {component_count} components. First 5:")
        for component in components:
            print(f"- {component.location} (ID: {component.id})")
            
        print("-" * 50)

def organize_components_by_relevance(location, components, limit=10):
    """Organize components by relevance to the location without using new fields"""
    print(f"\n==== Testing Relevance Ranking for {location} ====")
    
    # Create relevance scores dictionary
    scored_components = []
    
    # Get outcodes and counties for location
    outcodes = get_outcodes_for_location(location)
    location_data = get_all_data_for_location(location)
    counties = location_data.get("counties", [])
    
    # Score each component
    for component in components:
        # Default relevance
        relevance = 0.1
        
        comp_location = (component.location or "").lower()
        
        # Direct match in location field (highest priority)
        if location.lower() in comp_location:
            relevance = 3.0
        # Match county name in location (high priority)
        elif any(county.lower() in comp_location for county in counties):
            relevance = 2.0
        # Match outcode in location (medium priority)
        elif any(outcode.lower() in comp_location.lower() for outcode in outcodes):
            relevance = 1.0
        
        scored_components.append({
            "component": component,
            "score": relevance
        })
    
    # Sort by relevance score (highest first)
    scored_components.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top results
    top_results = scored_components[:limit]
    
    print(f"Top {len(top_results)} components by relevance:")
    for i, result in enumerate(top_results):
        component = result["component"]
        score = result["score"]
        print(f"{i+1}. [{score:.1f}] {component.location}")
        
    print("-" * 50)
    
    return top_results

def test_relevance_ranking():
    """Test the relevance ranking system"""
    print("\n==== Testing Relevance Ranking ====")
    
    locations = ["nottingham", "london", "battersea"]
    
    for location in locations:
        # Get outcodes for this location
        outcodes = get_outcodes_for_location(location)
        
        # Build search filter - only using location since our DB might not have the new fields yet
        location_filter = Q(location__icontains=location)
        
        # Add postcode searches using icontains on location
        postcode_filter = Q()
        for outcode in outcodes:
            postcode_filter |= Q(location__icontains=outcode)
            
        # Combine filters with OR
        combined_filter = location_filter | postcode_filter
        
        # Get components (up to 100 for testing)
        components = Component.objects.filter(combined_filter)[:100]
        
        # Rank by relevance
        organize_components_by_relevance(location, components)

if __name__ == "__main__":
    # Run all tests
    test_location_lookup()
    test_outcode_lookup()
    test_county_lookup()
    test_component_search()
    test_relevance_ranking() 