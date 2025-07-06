#!/usr/bin/env python3
"""
Network Request Analyzer - Extract IETF data from Tableau API calls
"""
import requests
import json
import re
import pandas as pd
from urllib.parse import parse_qs, urlparse, unquote
import time

def analyze_tableau_url(url):
    """Analyze a Tableau network request URL"""
    
    print(f"🔍 Analyzing URL: {url[:100]}...")
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    analysis = {
        'base_url': f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        'path': parsed.path,
        'query_params': query_params,
        'param_count': len(query_params),
        'interesting_params': []
    }
    
    # Look for interesting parameters
    interesting_keys = ['session_id', 'sheet', 'dashboard', 'workbook', 'vizql', 'bootstrap', 'render']
    
    for key, values in query_params.items():
        if any(interesting in key.lower() for interesting in interesting_keys):
            analysis['interesting_params'].append({
                'key': key,
                'value': values[0] if values else '',
                'description': f"Potential {key} parameter"
            })
    
    # Determine request type
    if 'bootstrap' in url:
        analysis['type'] = 'bootstrap'
        analysis['description'] = 'Initial Tableau session setup'
    elif 'render-tooltip' in url:
        analysis['type'] = 'tooltip'
        analysis['description'] = 'Tooltip data request'
    elif 'vizql' in url:
        analysis['type'] = 'vizql'
        analysis['description'] = 'Tableau visualization query'
    elif 'sessions' in url:
        analysis['type'] = 'session'
        analysis['description'] = 'Session management'
    else:
        analysis['type'] = 'unknown'
        analysis['description'] = 'Unknown request type'
    
    return analysis

def extract_session_info_from_url(url):
    """Extract session information from Tableau URL"""
    
    # Look for session IDs in various formats
    session_patterns = [
        r'sessions/([A-F0-9]+)',
        r'sessionId=([A-F0-9]+)',
        r'session_id=([A-F0-9]+)',
        r'/([A-F0-9]{32,})',
    ]
    
    session_info = {}
    
    for pattern in session_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            session_info['session_id'] = match.group(1)
            break
    
    # Look for workbook/sheet info
    workbook_match = re.search(r'workbook=([^&]+)', url)
    if workbook_match:
        session_info['workbook'] = unquote(workbook_match.group(1))
    
    sheet_match = re.search(r'sheet=([^&]+)', url)
    if sheet_match:
        session_info['sheet'] = unquote(sheet_match.group(1))
    
    return session_info

def try_reconstruct_api_calls():
    """Try to reconstruct Tableau API calls based on common patterns"""
    
    print("🔧 Attempting to reconstruct Tableau API calls...")
    
    # Common Tableau Public patterns
    base_urls = [
        "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard",
        "https://public.tableau.com/views/IETFProjectMap/MapDashboard"
    ]
    
    # Try to get initial page to find session info
    initial_url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
    
    try:
        print(f"📡 Fetching initial page: {initial_url}")
        response = requests.get(initial_url, timeout=30)
        
        if response.status_code == 200:
            print(f"   ✅ Got response: {len(response.text)} characters")
            
            # Look for embedded session info or API endpoints
            session_patterns = [
                r'"sessionId":"([^"]+)"',
                r"'sessionId':'([^']+)'",
                r'sessionId=([A-F0-9]+)',
                r'sessions/([A-F0-9]+)',
                r'"vizqlRoot":"([^"]+)"',
                r'"bootstrapSession":"([^"]+)"'
            ]
            
            found_sessions = {}
            for pattern in session_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    found_sessions[pattern] = matches[:3]  # First 3 matches
            
            print(f"   🔍 Session patterns found: {len(found_sessions)}")
            for pattern, matches in found_sessions.items():
                print(f"     {pattern}: {matches}")
            
            # Look for API endpoint patterns
            api_patterns = [
                r'(https://[^"]+/vizql/[^"]+)',
                r'(https://[^"]+/sessions/[^"]+)',
                r'(/vizql/w/[^"]+)',
                r'(/sessions/[^"]+)'
            ]
            
            found_apis = {}
            for pattern in api_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    found_apis[pattern] = list(set(matches))[:3]  # Unique, first 3
            
            print(f"   🌐 API endpoints found: {len(found_apis)}")
            for pattern, matches in found_apis.items():
                print(f"     {pattern}: {matches}")
            
            return {
                'page_content': response.text,
                'session_info': found_sessions,
                'api_endpoints': found_apis,
                'status_code': response.status_code
            }
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error fetching page: {e}")
        return None

def try_bootstrap_request():
    """Try to make a bootstrap request to get session info"""
    
    print("🚀 Attempting bootstrap request...")
    
    bootstrap_url = "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/bootstrapSession/sessions/"
    
    # Common bootstrap parameters
    bootstrap_params = {
        ':embed': 'n',
        ':showVizHome': 'no',
        ':apiID': 'host0',
        ':language': 'en-US',
        ':format': 'json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no'
    }
    
    try:
        print(f"📡 POST {bootstrap_url}")
        response = requests.post(bootstrap_url, data=bootstrap_params, headers=headers, timeout=30)
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Content length: {len(response.text)}")
        
        if response.text:
            print(f"   Sample content: {response.text[:200]}...")
            
            # Try to parse as JSON
            try:
                json_data = response.json()
                return json_data
            except:
                # Look for JSON in the response
                json_matches = re.findall(r'(\{.*?\})', response.text)
                if json_matches:
                    print(f"   Found {len(json_matches)} potential JSON objects")
                    for i, match in enumerate(json_matches[:3]):
                        try:
                            parsed = json.loads(match)
                            print(f"     JSON {i+1}: {list(parsed.keys())}")
                            return parsed
                        except:
                            continue
        
        return {'raw_response': response.text, 'status_code': response.status_code}
        
    except Exception as e:
        print(f"   ❌ Bootstrap error: {e}")
        return None

def manual_url_analysis():
    """Provide manual URL analysis instructions"""
    
    print("\n🛠️  Manual Network Request Analysis")
    print("=" * 50)
    print()
    print("Since automated discovery is challenging, here's how to extract network requests manually:")
    print()
    print("1. 🌐 Open browser to: https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no")
    print("2. 🔧 Open Developer Tools (F12)")
    print("3. 📡 Go to Network tab")
    print("4. 🔄 Refresh the page")
    print("5. 🖱️  Click on a map marker")
    print("6. 📋 Look for requests containing:")
    print("   - 'render-tooltip'")
    print("   - 'vizql'")
    print("   - 'sessions'")
    print("7. 🔗 Right-click the request → Copy → Copy as cURL")
    print("8. 📝 Paste the cURL command below for analysis")
    print()
    
    # Provide example of what to look for
    example_patterns = [
        "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{SESSION_ID}/commands/tabdoc/render-tooltip-server",
        "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{SESSION_ID}/commands/tabdoc/select",
        "https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/bootstrapSession/sessions/"
    ]
    
    print("🎯 Example URL patterns to look for:")
    for pattern in example_patterns:
        print(f"   {pattern}")
    print()

def analyze_curl_command(curl_command):
    """Analyze a cURL command and extract the request details"""
    
    print(f"🔍 Analyzing cURL command...")
    
    # Extract URL
    url_match = re.search(r"curl '([^']+)'", curl_command)
    if not url_match:
        url_match = re.search(r'curl "([^"]+)"', curl_command)
    
    if url_match:
        url = url_match.group(1)
        print(f"   URL: {url}")
        
        # Analyze the URL
        analysis = analyze_tableau_url(url)
        
        # Extract headers
        header_matches = re.findall(r"-H '([^:]+): ([^']+)'", curl_command)
        if not header_matches:
            header_matches = re.findall(r'-H "([^:]+): ([^"]+)"', curl_command)
        
        headers = dict(header_matches)
        
        # Extract data/body
        data_match = re.search(r"--data-raw '([^']+)'", curl_command)
        if not data_match:
            data_match = re.search(r'--data-raw "([^"]+)"', curl_command)
        
        data = data_match.group(1) if data_match else None
        
        return {
            'url': url,
            'analysis': analysis,
            'headers': headers,
            'data': data
        }
    else:
        print("   ❌ Could not extract URL from cURL command")
        return None

def main():
    print("🌐 Tableau Network Request Analyzer")
    print("🎯 Goal: Extract IETF project data from API calls")
    print()
    
    # Try automated discovery first
    print("📡 Step 1: Automated Discovery")
    page_info = try_reconstruct_api_calls()
    
    if page_info:
        print(f"   ✅ Got page info with {len(page_info.get('session_info', {}))} session patterns")
        
        # Save page analysis
        with open("tableau_page_analysis.json", "w") as f:
            json.dump(page_info, f, indent=2, default=str)
        print("   💾 Saved page analysis: tableau_page_analysis.json")
    
    # Try bootstrap
    print("\n🚀 Step 2: Bootstrap Request")
    bootstrap_info = try_bootstrap_request()
    
    if bootstrap_info:
        print("   ✅ Got bootstrap response")
        
        # Save bootstrap analysis
        with open("tableau_bootstrap_analysis.json", "w") as f:
            json.dump(bootstrap_info, f, indent=2, default=str)
        print("   💾 Saved bootstrap analysis: tableau_bootstrap_analysis.json")
    
    # Provide manual instructions
    print("\n🛠️  Step 3: Manual Analysis")
    manual_url_analysis()
    
    # Create a template for manual analysis
    template_script = '''#!/usr/bin/env python3
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
'''
    
    with open("manual_request_template.py", "w") as f:
        f.write(template_script)
    
    print("📝 Created manual analysis template: manual_request_template.py")
    print()
    print("🎯 Next Steps:")
    print("1. Follow the manual instructions above")
    print("2. Copy a network request from browser")
    print("3. Paste the details into manual_request_template.py")
    print("4. Run the template to extract data")
    print()
    print("💡 Alternative: If you can copy a cURL command, I can analyze it directly!")

if __name__ == "__main__":
    main()