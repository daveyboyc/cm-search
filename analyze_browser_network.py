#!/usr/bin/env python3
"""
Analyze Tableau network requests from browser console output
"""
import json
import re
import requests
from urllib.parse import parse_qs, urlparse, unquote

def analyze_tableau_network_request(url):
    """Analyze a Tableau network request URL to understand its structure"""
    parsed = urlparse(url)
    
    analysis = {
        "base_url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        "path": parsed.path,
        "query_params": parse_qs(parsed.query),
        "fragment": parsed.fragment
    }
    
    # Look for specific Tableau patterns
    if "render-tooltip-server" in url:
        analysis["type"] = "tooltip_render"
        analysis["description"] = "Tableau tooltip rendering request"
    elif "bootstrap" in url:
        analysis["type"] = "bootstrap"
        analysis["description"] = "Tableau session bootstrap"
    elif "sessions" in url:
        analysis["type"] = "session"
        analysis["description"] = "Tableau session management"
    elif "vizql" in url:
        analysis["type"] = "vizql"
        analysis["description"] = "Tableau VizQL query"
    
    return analysis

def extract_session_info_from_url(url):
    """Extract session information from Tableau URLs"""
    # Look for session patterns in URL
    session_patterns = [
        r"sessions/([A-F0-9]+)",
        r"bootstrap-session/([A-F0-9]+)",
        r"vizql_root/([^/]+)"
    ]
    
    session_info = {}
    
    for pattern in session_patterns:
        match = re.search(pattern, url)
        if match:
            session_info["session_id"] = match.group(1)
            break
    
    # Extract other useful parameters
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    useful_params = ["sheet", "dashboard", "worksheet", "viz", "site_root"]
    for param in useful_params:
        if param in params:
            session_info[param] = params[param][0]
    
    return session_info

def create_request_template(base_url, session_info):
    """Create a template for making similar requests"""
    template = {
        "base_url": base_url,
        "session_info": session_info,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://public.tableau.com/",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache"
        }
    }
    return template

def simulate_tooltip_request(session_info, x_coord=500, y_coord=300):
    """Simulate a tooltip request for given coordinates"""
    if "session_id" not in session_info:
        print("❌ No session ID found")
        return None
    
    # Build tooltip request URL (this is an approximation)
    base_url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/render-tooltip-server"
    
    params = {
        "session_id": session_info["session_id"],
        "sheet": session_info.get("sheet", "MapDashboard"),
        "x": x_coord,
        "y": y_coord,
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://public.tableau.com/views/IETFProjectMap/MapDashboard",
        "Accept": "*/*"
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            print(f"❌ Request failed with status {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None

def main():
    print("🔍 Tableau Network Request Analyzer")
    print("=" * 50)
    
    # Example URLs from browser network tab (replace with actual URLs)
    example_urls = [
        # Add the actual URLs you see in the browser network tab here
        "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/render-tooltip-server?...",
        "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/bootstrap-session/...",
    ]
    
    print("📝 How to use this analyzer:")
    print("1. Open the Tableau page in your browser")
    print("2. Open Developer Tools (F12) and go to Network tab")
    print("3. Interact with the map (hover/click on markers)")
    print("4. Copy the network request URLs and paste them below")
    print()
    
    # Interactive mode
    while True:
        print("\n🔗 Paste a network request URL (or 'quit' to exit):")
        user_url = input().strip()
        
        if user_url.lower() in ['quit', 'exit', '']:
            break
        
        if not user_url.startswith('http'):
            print("❌ Please enter a valid URL starting with http")
            continue
        
        print(f"\n🔍 Analyzing: {user_url[:80]}...")
        
        # Analyze the URL
        analysis = analyze_tableau_network_request(user_url)
        print(f"📊 Request type: {analysis.get('type', 'unknown')}")
        print(f"📝 Description: {analysis.get('description', 'Unknown request')}")
        
        # Extract session info
        session_info = extract_session_info_from_url(user_url)
        if session_info:
            print(f"🔑 Session info found: {list(session_info.keys())}")
            
            # Create request template
            template = create_request_template(analysis["base_url"], session_info)
            
            # Save template for later use
            filename = f"tableau_request_template_{int(time.time())}.json"
            with open(filename, "w") as f:
                json.dump(template, f, indent=2)
            print(f"💾 Saved request template to: {filename}")
            
            # If it's a tooltip request, try to simulate it
            if analysis.get("type") == "tooltip_render":
                print("🎯 Attempting to simulate tooltip request...")
                result = simulate_tooltip_request(session_info)
                if result:
                    result_file = f"tooltip_response_{int(time.time())}.txt"
                    with open(result_file, "w") as f:
                        f.write(result)
                    print(f"✅ Saved tooltip response to: {result_file}")
        else:
            print("❌ No session information found in URL")
        
        print("-" * 50)

if __name__ == "__main__":
    import time
    main() 