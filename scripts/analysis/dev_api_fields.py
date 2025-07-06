#!/usr/bin/env python3
"""
Test script to see what fields are in the API response
"""
import requests
import json

def test_api_fields():
    url = "https://api.neso.energy/api/3/action/datastore_search"
    params = {
        "resource_id": "25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6",
        "limit": 5  # Just get 5 records to see the structure
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        print("API Response structure:")
        print(f"Success: {data.get('success')}")
        print(f"Total records available: {data.get('result', {}).get('total', 'N/A')}")
        
        records = data.get("result", {}).get("records", [])
        print(f"Records returned: {len(records)}")
        
        if records:
            print("\nFirst record structure:")
            first_record = records[0]
            for key, value in first_record.items():
                print(f"  {key}: {value}")
            
            print("\nAll field names:")
            print(list(first_record.keys()))
        
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_api_fields()