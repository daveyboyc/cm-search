#!/usr/bin/env python
"""
Test script for the GPT API integration with the UK Capacity Market search app.
This script sends test queries to the API endpoint and validates the responses.
"""

import requests
import json
import sys
import os

# Configuration
API_URL = os.environ.get('API_URL', 'http://localhost:8000/api/gpt-search/')
API_KEY = os.environ.get('API_KEY', 'your_custom_api_key_for_auth')  # Match the key in settings

def test_gpt_search_api(query):
    """Test the GPT search API with a given query"""
    print(f"Testing query: '{query}'")
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }
    
    data = {
        'query': query
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        
        # Print status code
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse and pretty-print the JSON response
            result = response.json()
            
            # Print summary
            print(f"Summary: {result.get('summary', 'No summary available')}")
            print(f"Results count: {result.get('results_count', 0)}")
            
            # Print first few results
            components = result.get('components', [])
            for i, component in enumerate(components[:3]):  # Show first 3 components
                print(f"\nComponent {i+1}:")
                print(f"  CMU ID: {component.get('cmu_id', 'N/A')}")
                print(f"  Company: {component.get('company_name', 'N/A')}")
                print(f"  Location: {component.get('location', 'N/A')}")
                print(f"  Technology: {component.get('technology', 'N/A')}")
                print(f"  Delivery Year: {component.get('delivery_year', 'N/A')}")
            
            if len(components) > 3:
                print(f"\n... and {len(components) - 3} more components")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n" + "-"*50 + "\n")

def main():
    """Main function to run tests"""
    test_queries = [
        # Basic queries
        "Show me all components in Nottingham",
        "How many CHPs are in London?",
        "Find nuclear power plants in the UK",
        
        # Time-specific queries
        "Show components from the 2022 auction",
        "What facilities were in T-4 2020?",
        
        # Specific facility queries
        "Tell me about the Elephant CHP",
        "Find information about QMC hospital",
        
        # Technology-specific queries
        "How many gas generators are there?",
        "Show all DSR components",
        
        # Complex queries
        "How many solar farms were in the T-1 2023 auction?",
        "What's the total capacity of battery storage in Manchester?"
    ]
    
    # Use command line args if provided, otherwise use the test set
    queries_to_test = sys.argv[1:] if len(sys.argv) > 1 else test_queries
    
    for query in queries_to_test:
        test_gpt_search_api(query)

if __name__ == "__main__":
    main() 