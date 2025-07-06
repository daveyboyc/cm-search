#!/usr/bin/env python3
"""
Process cURL Command - Analyze Tableau network request
"""
import requests
import json
import re
from urllib.parse import parse_qs, urlparse, unquote

def process_curl_command():
    """
    Paste your cURL command in the curl_command variable below
    """
    
    # PASTE YOUR CURL COMMAND HERE (replace the example):
    curl_command = """
curl 'https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/A8F364831F894B44BCCE6DFAEA5EF166-0:0/commands/tabsrv/render-tooltip-server' \\
  -H 'accept: text/javascript' \\
  -H 'accept-language: en-US,en;q=0.9' \\
  -H 'content-type: multipart/form-data; boundary=RIzqNJrD' \\
  -H 'cookie: tableau_public_negotiated_locale=en-us; tableau_locale=en; OptanonAlertBoxClosed=2025-06-09T11:21:02.134Z; OptanonConsent=isGpcEnabled=0&datestamp=Mon+Jun+16+2025+14%3A26%3A19+GMT%2B0100+(British+Summer+Time)&version=6.17.0&isIABGlobal=false&hosts=&consentId=8515b513-2327-4d17-9212-8e331ed94864&interactionCount=1&landingPath=NotLandingPage&groups=1%3A1%2C2%3A1%2C3%3A1%2C4%3A1&geolocation=GB%3BENG&AwaitingReconsent=false; _gid=GA1.2.1551086354.1750080381; _ga=GA1.1.1726352879.1750080381; _gcl_au=1.1.1685043425.1750080381; _ga_8YLN0SNXVS=GS2.1.s1750150373$o3$g0$t1750150373$j60$l0$h0' \\
  -H 'origin: https://public.tableau.com' \\
  -H 'priority: u=1, i' \\
  -H 'referer: https://public.tableau.com/views/IETFProjectMap/MapDashboard?%3Adisplay_static_image=y&%3Aembed=true&%3Aembed=y&%3Alanguage=en-US&%3AshowVizHome=n&%3AapiID=host0' \\
  -H 'sec-ch-ua: "Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"' \\
  -H 'sec-ch-ua-mobile: ?0' \\
  -H 'sec-ch-ua-platform: "macOS"' \\
  -H 'sec-fetch-dest: empty' \\
  -H 'sec-fetch-mode: cors' \\
  -H 'sec-fetch-site: same-origin' \\
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \\
  -H 'x-requested-with: XMLHttpRequest' \\
  -H 'x-tableau-version: 2025.1' \\
  -H 'x-tsi-active-tab: Map%20Dashboard' \\
  --data-raw $'--RIzqNJrD\\r\\nContent-Disposition: form-data; name="worksheet"\\r\\n\\r\\nMap External\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="dashboard"\\r\\n\\r\\nMap Dashboard\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="vizRegionRect"\\r\\n\\r\\n{"r":"viz","x":-1,"y":-1,"w":0,"h":0,"fieldVector":null}\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="allowHoverActions"\\r\\n\\r\\ntrue\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="allowPromptText"\\r\\n\\r\\ntrue\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="allowWork"\\r\\n\\r\\nfalse\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="useInlineImages"\\r\\n\\r\\ntrue\\r\\n--RIzqNJrD\\r\\nContent-Disposition: form-data; name="telemetryCommandId"\\r\\n\\r\\n1ituvep79$0j1n-1g-eo-0z-j412dy\\r\\n--RIzqNJrD--\\r\\n'
"""
    
    if "PASTE_YOUR_CURL_COMMAND_HERE" in curl_command:
        print("❌ Please paste your actual cURL command in the curl_command variable")
        print("\n📋 Instructions:")
        print("1. Go to https://public.tableau.com/views/IETFProjectMap/MapDashboard")
        print("2. Open DevTools (F12) → Network tab")
        print("3. Click on a map marker")
        print("4. Find the 'render-tooltip-server' request")
        print("5. Right-click → Copy → Copy as cURL")
        print("6. Paste it in the curl_command variable above")
        return
    
    print("🔍 Processing cURL command...")
    
    # Extract URL
    url_match = re.search(r"curl '([^']+)'", curl_command)
    if not url_match:
        url_match = re.search(r'curl "([^"]+)"', curl_command)
    
    if not url_match:
        print("❌ Could not extract URL")
        return
    
    url = url_match.group(1)
    print(f"📍 URL: {url}")
    
    # Extract headers
    header_matches = re.findall(r"-H '([^:]+):\s*([^']+)'", curl_command)
    if not header_matches:
        header_matches = re.findall(r'-H "([^:]+):\s*([^"]+)"', curl_command)
    
    headers = dict(header_matches)
    print(f"📨 Headers: {len(headers)} found")
    
    # Extract data
    data_match = re.search(r"--data-raw '([^']+)'", curl_command, re.DOTALL)
    if not data_match:
        data_match = re.search(r'--data-raw "([^"]+)"', curl_command, re.DOTALL)
    
    data = data_match.group(1) if data_match else None
    
    if data:
        print(f"📦 Data payload: {len(data)} characters")
    
    # Determine request type
    if 'render-tooltip' in url:
        print("🎯 Type: Tooltip request - This should contain marker data!")
    elif 'select' in url:
        print("🎯 Type: Selection request")
    elif 'bootstrap' in url:
        print("🎯 Type: Bootstrap request")
    else:
        print("🎯 Type: Unknown")
    
    # Make the request
    try:
        print("\n🚀 Making request...")
        
        kwargs = {
            'url': url,
            'headers': headers,
            'timeout': 30
        }
        
        if data:
            try:
                kwargs['json'] = json.loads(data)
            except:
                kwargs['data'] = data
        
        response = requests.post(**kwargs)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"📏 Response length: {len(response.text)} characters")
            
            # Save response
            with open("tableau_tooltip_response.txt", "w") as f:
                f.write(response.text)
            print("💾 Saved response: tableau_tooltip_response.txt")
            
            # Try to parse as JSON
            try:
                json_data = response.json()
                with open("tableau_tooltip_response.json", "w") as f:
                    json.dump(json_data, f, indent=2)
                print("💾 Saved JSON: tableau_tooltip_response.json")
                
                # Look for tooltip content
                if 'vqlCmdResponse' in json_data:
                    cmd_response = json_data['vqlCmdResponse']
                    if 'layoutStatus' in cmd_response:
                        layout = cmd_response['layoutStatus']
                        if 'applicationPresModel' in layout:
                            app_model = layout['applicationPresModel']
                            print("🔍 Found application presentation model")
                            
                            # Look for tooltip data
                            if 'workbookPresModel' in app_model:
                                workbook = app_model['workbookPresModel']
                                if 'dashboardPresModel' in workbook:
                                    dashboard = workbook['dashboardPresModel']
                                    print("🎯 Found dashboard data structure")
                
            except:
                print("📝 Response is not JSON, checking raw content...")
                
                # Look for patterns in raw text
                project_patterns = [
                    r'Company[:\s]*([^<\n]+)',
                    r'Project[:\s]*([^<\n]+)', 
                    r'Amount[:\s]*([^<\n]+)',
                    r'Location[:\s]*([^<\n]+)',
                    r'Technology[:\s]*([^<\n]+)',
                    r'£([0-9,]+)',
                    r'(\w+\s+\w+\s+(?:Ltd|Limited|PLC))',
                ]
                
                found_data = {}
                for pattern in project_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    if matches:
                        found_data[pattern] = matches[:5]  # First 5 matches
                
                if found_data:
                    print("🎉 Found project data patterns!")
                    for pattern, matches in found_data.items():
                        print(f"   {pattern}: {matches}")
                    
                    with open("extracted_project_data.json", "w") as f:
                        json.dump(found_data, f, indent=2)
                    print("💾 Saved extracted data: extracted_project_data.json")
                else:
                    print("⚠️ No obvious project data patterns found")
                    print(f"📝 Sample response: {response.text[:300]}...")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"📝 Error: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Request error: {e}")

if __name__ == "__main__":
    process_curl_command() 