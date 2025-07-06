#!/usr/bin/env python3
"""
cURL Command Analyzer - Process network requests copied from browser
"""
import requests
import json
import re
import sys
from urllib.parse import parse_qs, urlparse, unquote

def parse_curl_command(curl_command):
    """Parse a cURL command and extract all components"""
    
    print("🔍 Parsing cURL command...")
    
    # Extract URL - handle both single and double quotes
    url_patterns = [
        r"curl '([^']+)'",
        r'curl "([^"]+)"',
        r"curl ([^\s]+)",  # URL without quotes
    ]
    
    url = None
    for pattern in url_patterns:
        match = re.search(pattern, curl_command)
        if match:
            url = match.group(1)
            break
    
    if not url:
        print("❌ Could not extract URL from cURL command")
        return None
    
    print(f"   📍 URL: {url}")
    
    # Extract method (default to GET)
    method_match = re.search(r'-X\s+([A-Z]+)', curl_command)
    method = method_match.group(1) if method_match else 'GET'
    
    # Extract headers
    header_patterns = [
        r"-H '([^:]+):\s*([^']+)'",
        r'-H "([^:]+):\s*([^"]+)"',
        r'--header "([^:]+):\s*([^"]+)"',
        r"--header '([^:]+):\s*([^']+)'"
    ]
    
    headers = {}
    for pattern in header_patterns:
        matches = re.findall(pattern, curl_command)
        for name, value in matches:
            headers[name.strip()] = value.strip()
    
    # Extract data/body
    data_patterns = [
        r"--data-raw '([^']+)'",
        r'--data-raw "([^"]+)"',
        r"--data '([^']+)'",
        r'--data "([^"]+)"',
        r"-d '([^']+)'",
        r'-d "([^"]+)"'
    ]
    
    data = None
    for pattern in data_patterns:
        match = re.search(pattern, curl_command, re.DOTALL)
        if match:
            data = match.group(1)
            break
    
    return {
        'url': url,
        'method': method,
        'headers': headers,
        'data': data
    }

def analyze_tableau_request(parsed_request):
    """Analyze a parsed Tableau request"""
    
    url = parsed_request['url']
    print(f"\n🔍 Analyzing Tableau request: {url}")
    
    # Determine request type
    request_types = {
        'bootstrap': 'Session initialization',
        'render-tooltip': 'Tooltip data (JACKPOT! This has marker data)',
        'select': 'Marker selection',
        'vizql': 'Visualization query',
        'sessions': 'Session management',
        'commands': 'Tableau command execution'
    }
    
    request_type = 'unknown'
    description = 'Unknown request type'
    
    for req_type, desc in request_types.items():
        if req_type in url.lower():
            request_type = req_type
            description = desc
            break
    
    print(f"   🎯 Type: {request_type} - {description}")
    
    # Extract session ID
    session_patterns = [
        r'/sessions/([A-F0-9]+)',
        r'sessionId=([A-F0-9]+)',
        r'session_id=([A-F0-9]+)'
    ]
    
    session_id = None
    for pattern in session_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            session_id = match.group(1)
            break
    
    if session_id:
        print(f"   🔑 Session ID: {session_id}")
    
    # Analyze data payload
    if parsed_request['data']:
        print(f"   📦 Data payload: {len(parsed_request['data'])} characters")
        
        # Try to parse as JSON
        try:
            json_data = json.loads(parsed_request['data'])
            print(f"   📄 JSON structure: {list(json_data.keys())}")
            return json_data
        except:
            print(f"   📝 Raw data preview: {parsed_request['data'][:100]}...")
    
    return {
        'url': url,
        'type': request_type,
        'session_id': session_id,
        'description': description
    }

def make_request(parsed_request):
    """Execute the parsed request"""
    
    print(f"\n🚀 Executing {parsed_request['method']} request...")
    
    try:
        # Prepare request parameters
        kwargs = {
            'url': parsed_request['url'],
            'headers': parsed_request['headers'],
            'timeout': 30
        }
        
        # Add data if present
        if parsed_request['data']:
            # Try JSON first
            try:
                kwargs['json'] = json.loads(parsed_request['data'])
            except:
                kwargs['data'] = parsed_request['data']
        
        # Make request
        if parsed_request['method'].upper() == 'POST':
            response = requests.post(**kwargs)
        else:
            response = requests.get(**kwargs)
        
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📏 Response length: {len(response.text)} characters")
        
        # Try to parse response
        if response.status_code == 200:
            try:
                json_response = response.json()
                print(f"   📊 JSON keys: {list(json_response.keys())}")
                
                # Save response
                with open("tableau_response.json", "w") as f:
                    json.dump(json_response, f, indent=2, default=str)
                print(f"   💾 Saved response: tableau_response.json")
                
                return json_response
                
            except:
                print(f"   📝 Raw response preview: {response.text[:200]}...")
                
                # Save raw response
                with open("tableau_response.txt", "w") as f:
                    f.write(response.text)
                print(f"   💾 Saved raw response: tableau_response.txt")
                
                return response.text
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   📝 Error content: {response.text[:200]}...")
            return None
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return None

def extract_project_data(response_data):
    """Extract project information from response data"""
    
    print("\n🎯 Extracting project data...")
    
    if isinstance(response_data, dict):
        # Look for common data patterns
        data_keys = ['tooltip', 'data', 'content', 'results', 'vizData', 'vqlCmdResponse']
        
        for key in data_keys:
            if key in response_data:
                print(f"   🔍 Found data in '{key}' field")
                
                data = response_data[key]
                if isinstance(data, str):
                    # Look for HTML content with project info
                    project_patterns = [
                        r'Company:\s*([^<\n]+)',
                        r'Project:\s*([^<\n]+)',
                        r'Amount:\s*([^<\n]+)',
                        r'Location:\s*([^<\n]+)',
                        r'Technology:\s*([^<\n]+)',
                        r'£([0-9,]+)',  # Money amounts
                        r'(\w+\s+\w+\s+Ltd|Limited|PLC)',  # Company names
                    ]
                    
                    found_data = {}
                    for pattern in project_patterns:
                        matches = re.findall(pattern, data, re.IGNORECASE)
                        if matches:
                            found_data[pattern] = matches
                    
                    if found_data:
                        print(f"   ✅ Extracted {len(found_data)} data patterns")
                        for pattern, matches in found_data.items():
                            print(f"     {pattern}: {matches[:3]}")  # First 3 matches
                        
                        return found_data
    
    return None

def main():
    print("🌐 Tableau cURL Command Analyzer")
    print("🎯 Paste your cURL command below (or pass as argument)")
    print("=" * 50)
    
    # Get cURL command
    if len(sys.argv) > 1:
        curl_command = sys.argv[1]
    else:
        print("\n📋 Paste your cURL command here:")
        print("(You can get this by right-clicking a network request in browser → Copy → Copy as cURL)")
        print("\nEnter command (press Enter twice when done):")
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "" and lines:
                    break
                lines.append(line)
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                return
        
        curl_command = "\n".join(lines)
    
    if not curl_command.strip():
        print("❌ No cURL command provided")
        return
    
    # Parse the command
    parsed = parse_curl_command(curl_command)
    if not parsed:
        return
    
    # Analyze the request
    analysis = analyze_tableau_request(parsed)
    
    # Make the request
    response = make_request(parsed)
    
    # Extract project data if possible
    if response:
        project_data = extract_project_data(response)
        
        if project_data:
            print("\n🎉 SUCCESS! Found project data patterns")
            
            # Save extracted data
            with open("extracted_project_data.json", "w") as f:
                json.dump(project_data, f, indent=2, default=str)
            print("   💾 Saved extracted data: extracted_project_data.json")
        else:
            print("\n⚠️  No project data patterns found in response")
            print("   💡 This might be a different type of request")
    
    print("\n🎯 Summary:")
    print(f"   URL Type: {analysis.get('type', 'unknown')}")
    print(f"   Session ID: {analysis.get('session_id', 'not found')}")
    print(f"   Response: {'Success' if response else 'Failed'}")

if __name__ == "__main__":
    main()