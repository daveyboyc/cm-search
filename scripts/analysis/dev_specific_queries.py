#!/usr/bin/env python
"""
Test specific search queries through the GPT API to diagnose issues
"""

import requests
import json
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test GPT API search queries')
parser.add_argument('--local', action='store_true', help='Use local server instead of Heroku')
parser.add_argument('--query', type=str, help='Single query to test')
args = parser.parse_args()

# Configuration - use local server by default, can be overridden with --local=False
BASE_URL = "http://localhost:8000" if args.local else "https://neso-cmr-search-da0169863eae.herokuapp.com"
API_URL = f"{BASE_URL}/api/gpt-search/"
API_KEY = "your_custom_api_key_for_auth"  # The default key from our code

# Also test the direct search endpoint
DIRECT_SEARCH_URL = f"{BASE_URL}/"

print(f"Using {'LOCAL' if args.local else 'HEROKU'} server at: {BASE_URL}")

# Test queries that should definitely return results
TEST_QUERIES = [
    "SW11",
    "London",
    "Nottingham",
    "CHP",
    "gas",
    "Give me results with post code SW11",
    "Are there CHPs in London",
    "Show me power stations in Nottingham"
]

# If a single query was provided, only test that
if args.query:
    TEST_QUERIES = [args.query]
    print(f"Testing only query: '{args.query}'")

def test_direct_search(query):
    """Test the direct search endpoint which should return HTML results"""
    print(f"\n=== Testing DIRECT SEARCH: '{query}' ===")
    
    try:
        response = requests.get(DIRECT_SEARCH_URL, params={'q': query})
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Check if there are search results by looking for specific HTML patterns
            html = response.text
            
            # Count component results by looking for component links
            component_link_count = html.count('component/')
            
            # Count company results
            company_link_count = html.count('company/')
            
            print(f"Direct search results (HTML):")
            print(f"  Component links found: {component_link_count}")
            print(f"  Company links found: {company_link_count}")
            
            if component_link_count == 0 and company_link_count == 0:
                print("  No results found in HTML response")
        else:
            print(f"Error response: {response.text[:200]}")
    
    except Exception as e:
        print(f"Exception: {e}")

def test_query(query):
    """Send a test query to the API and print the results"""
    print(f"\n=== Testing GPT API query: '{query}' ===")
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }
    
    data = {
        'query': query
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Results count: {result.get('results_count', 0)}")
            
            # Print extracted parameters - this would help debug if it's parsing correctly
            print(f"Original query: {result.get('query', '')}")
            
            # Print entire raw response for debugging
            print(f"Raw JSON response: {json.dumps(result, indent=2)[:500]}...")
            
            # Print first few results if any
            components = result.get('components', [])
            if components:
                print("\nFirst 3 results:")
                for i, comp in enumerate(components[:3]):
                    print(f"  {i+1}. {comp.get('location', 'No location')} - {comp.get('company_name', 'No company')}")
            else:
                print("\nNo results found in API response")
                
            # Print any error message
            if result.get('error'):
                print(f"Error: {result.get('error')}")
        else:
            print(f"Error response: {response.text}")
    
    except Exception as e:
        print(f"Exception: {e}")

def main():
    """Run tests for all queries"""
    for query in TEST_QUERIES:
        # First test the direct search endpoint
        test_direct_search(query)
        
        # Then test the GPT API
        test_query(query)
        print("-" * 80)

if __name__ == "__main__":
    main() 