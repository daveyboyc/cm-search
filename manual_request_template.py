#!/usr/bin/env python3
"""
Template for analyzing manually copied network requests
"""
import requests
import json

def analyze_manual_request():
    """
    Replace the variables below with actual values from browser network tab:
    """
    
    # PASTE YOUR VALUES HERE:
    session_id = "YOUR_SESSION_ID_HERE"  # From network request URL
    url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{session_id}/commands/tabdoc/render-tooltip-server"
    
    headers = {
        # PASTE HEADERS FROM BROWSER HERE
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard'
        # Add more headers as needed
    }
    
    data = {
        # PASTE POST DATA FROM BROWSER HERE
        # This will contain the marker selection information
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                print("JSON Response:")
                print(json.dumps(json_data, indent=2))
            except:
                print("Raw Response:")
                print(response.text)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_manual_request()
