#!/usr/bin/env python3
"""
Debug the actual API calls being made by checking Django logs and monitoring
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

import requests
import time

print("🔍 DEBUGGING ACTUAL API CALLS")
print("=" * 50)

base_url = "http://localhost:8000"

# Clear monitoring data first
try:
    from monitoring.simple_monitor import monitoring_data
    monitoring_data['api_calls'] = []
    monitoring_data['total_bytes'] = 0
    monitoring_data['endpoint_stats'] = {}
    print("✅ Cleared monitoring data")
except:
    print("⚠️ Monitoring not available")

print("\n🌐 Loading a company-map page and watching for API calls...")
print("-" * 50)

# Load the page
try:
    response = requests.get(f"{base_url}/company-map/GRIDBEYOND%2520LIMITED/", timeout=10)
    page_size = len(response.content) / 1024
    print(f"📄 Main page loaded: {page_size:.1f} KB")
    
    # Wait a moment for any async API calls
    time.sleep(2)
    
    # Check what monitoring captured
    try:
        from monitoring.simple_monitor import monitoring_data
        api_calls = monitoring_data['api_calls']
        total_bytes = monitoring_data['total_bytes']
        
        print(f"\n📊 MONITORING CAPTURED:")
        print(f"   API calls: {len(api_calls)}")
        print(f"   Total bytes: {total_bytes / 1024:.1f} KB")
        
        if api_calls:
            print(f"\n📋 ACTUAL API CALLS MADE:")
            for i, call in enumerate(api_calls, 1):
                size_kb = call['size'] / 1024
                endpoint = call['endpoint']
                print(f"   {i}. {endpoint}: {size_kb:.1f} KB")
        else:
            print(f"\n⚠️ No API calls captured by monitoring")
            print(f"   This suggests:")
            print(f"   1. API calls aren't going through monitored endpoints")
            print(f"   2. Monitoring decorators aren't working")
            print(f"   3. API calls are cached")
            
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")
        
except Exception as e:
    print(f"❌ Error loading page: {e}")

# Test specific API endpoints that might be called
print(f"\n🧪 TESTING SUSPECTED API ENDPOINTS:")
print("-" * 50)

api_tests = [
    "/api/search-geojson/?tech=All&show_active=true",
    "/api/map-data/?company=GRIDBEYOND%20LIMITED",
    "/api/component-map-detail/1/",
]

for api_url in api_tests:
    try:
        print(f"\n📡 Testing: {api_url}")
        response = requests.get(f"{base_url}{api_url}", timeout=5)
        
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            encoding = response.headers.get('content-encoding', 'none')
            content_type = response.headers.get('content-type', '')
            
            print(f"   Status: ✅ {response.status_code}")
            print(f"   Size: {size_kb:.1f} KB")
            print(f"   Encoding: {encoding}")
            print(f"   Type: {content_type}")
            
            if size_kb > 100:
                print(f"   🚨 LARGE API RESPONSE!")
                
                # If it's JSON, check the structure
                if 'json' in content_type:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if isinstance(value, list):
                                    print(f"      {key}: {len(value)} items")
                                else:
                                    print(f"      {key}: {type(value).__name__}")
                    except:
                        pass
        else:
            print(f"   Status: ❌ {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n💡 DEBUGGING CONCLUSIONS:")
print("="*50)
print("1. Check if pages are making automatic API calls")
print("2. Look for JavaScript that loads map data on page load")
print("3. Check if Google Maps is triggering API calls")
print("4. Consider monitoring at the web server level")
print("5. Use browser dev tools for complete picture")

print(f"\n🎯 IMMEDIATE ACTION:")
print("Open browser dev tools > Network tab")
print("Load a company-map page")
print("Look for large API responses in the network requests")
print("This will show the EXACT culprit causing 26% egress")