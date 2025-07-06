#!/usr/bin/env python3
"""
Live IETF Extractor - Real-time guidance for capturing Tableau data
"""
import requests
import json
import re
import time
from datetime import datetime

def test_session_validity(session_id):
    """Test if a session ID is still valid"""
    
    print(f"🔍 Testing session validity: {session_id}")
    
    # Try a simple bootstrap request to test session
    test_url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{session_id}/commands/tabsrv/render-tooltip-server"
    
    headers = {
        'accept': 'text/javascript',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("   ✅ Session is valid")
            return True
        elif response.status_code == 410:
            print("   ❌ Session expired (410)")
            return False
        elif response.status_code == 404:
            print("   ❌ Session not found (404)")
            return False
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing session: {e}")
        return False

def extract_session_from_curl(curl_command):
    """Extract session ID from cURL command"""
    
    session_match = re.search(r'/sessions/([A-F0-9-]+)', curl_command)
    if session_match:
        return session_match.group(1)
    return None

def analyze_curl_for_markers(curl_command):
    """Analyze cURL command to see if it contains marker-specific data"""
    
    print("🔍 Analyzing cURL command for marker data...")
    
    # Look for coordinates in vizRegionRect
    viz_rect_match = re.search(r'"vizRegionRect"[^}]+\{([^}]+)\}', curl_command)
    if viz_rect_match:
        viz_data = viz_rect_match.group(1)
        print(f"   📍 VizRegionRect: {viz_data}")
        
        # Check for specific coordinates
        if '"x":-1,"y":-1' in viz_data:
            print("   ⚠️ Generic coordinates detected (-1, -1)")
            print("   💡 This suggests no specific marker was clicked")
            return False
        elif '"x":' in viz_data and '"y":' in viz_data:
            x_match = re.search(r'"x":(\d+)', viz_data)
            y_match = re.search(r'"y":(\d+)', viz_data)
            if x_match and y_match:
                print(f"   ✅ Specific coordinates found: x={x_match.group(1)}, y={y_match.group(1)}")
                return True
    
    # Look for fieldVector data
    if '"fieldVector":null' in curl_command:
        print("   ⚠️ No fieldVector data (marker selection info)")
    else:
        print("   ✅ FieldVector data present")
        return True
    
    return False

def provide_session_guidance():
    """Provide guidance for getting a fresh session"""
    
    print("\n🔄 Getting a Fresh Session")
    print("=" * 40)
    print()
    print("Your Tableau session has expired. Here's how to get a fresh one:")
    print()
    print("1. 🌐 Open NEW browser tab/window")
    print("2. 🔄 Go to: https://public.tableau.com/views/IETFProjectMap/MapDashboard")
    print("3. ⏳ Wait for map to fully load (you'll see markers)")
    print("4. 🔧 Open DevTools (F12) → Network tab")
    print("5. 🗑️ Clear network log")
    print("6. 🎯 Click directly on a map marker (not hover!)")
    print("7. 📋 Look for 'render-tooltip-server' request")
    print("8. 📋 Copy as cURL and paste here")
    print()
    print("🔍 Signs of a good request:")
    print("   • Response size > 2KB")
    print("   • Shows project details in preview")
    print("   • Contains specific x,y coordinates (not -1,-1)")
    print()

def create_session_test_script():
    """Create a script to test session validity"""
    
    script_content = '''#!/usr/bin/env python3
"""
Session Tester - Quick test for Tableau session validity
"""
import requests
import sys

def test_session(session_id):
    url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{session_id}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Session {session_id} is VALID")
            return True
        elif response.status_code == 410:
            print(f"❌ Session {session_id} is EXPIRED")
            return False
        else:
            print(f"⚠️ Session {session_id} status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    else:
        session_id = input("Enter session ID: ")
    
    test_session(session_id)
'''
    
    with open("test_session.py", "w") as f:
        f.write(script_content)
    
    print("📝 Created session tester: test_session.py")
    print("   Usage: python test_session.py YOUR_SESSION_ID")

def analyze_current_status():
    """Analyze the current situation and provide next steps"""
    
    print("📊 Current Status Analysis")
    print("=" * 30)
    
    # Check what we've learned so far
    print("✅ What's Working:")
    print("   • API endpoint structure is correct")
    print("   • Authentication method works")
    print("   • Request format is proper")
    print("   • Session concept is understood")
    
    print("\n❌ Current Issues:")
    print("   • Session A8F364831F894B44BCCE6DFAEA5EF166-0:0 expired (410)")
    print("   • Previous requests were generic hovers, not marker clicks")
    print("   • Need fresh session + specific marker selection")
    
    print("\n🎯 What We Need:")
    print("   • Fresh session ID (from new browser visit)")
    print("   • Request from actual marker click")
    print("   • Coordinates other than x:-1, y:-1")
    print("   • Response size > 2KB with project data")
    
    print("\n🚀 Success Probability:")
    print("   📈 Very High - We've proven the concept works!")
    print("   🔧 Just need fresh session + proper marker click")

def main():
    print("🌐 Live IETF Data Extractor")
    print("🎯 Real-time guidance for Tableau data capture")
    print("=" * 50)
    
    # Analyze current status
    analyze_current_status()
    
    # Test the known session
    print(f"\n🔍 Testing Previous Session:")
    known_session = "A8F364831F894B44BCCE6DFAEA5EF166-0:0"
    is_valid = test_session_validity(known_session)
    
    if not is_valid:
        provide_session_guidance()
    
    # Create helper tools
    print(f"\n🛠️ Creating Helper Tools:")
    create_session_test_script()
    
    print(f"\n💡 Pro Tips:")
    print("   • Sessions expire quickly (5-10 minutes)")
    print("   • Marker clicks create larger responses than hovers")
    print("   • Look for fieldVector data in successful requests")
    print("   • x,y coordinates should be positive numbers")
    
    print(f"\n📋 Ready for your next cURL command!")
    print("   Paste it here when you have a fresh session")

if __name__ == "__main__":
    main() 