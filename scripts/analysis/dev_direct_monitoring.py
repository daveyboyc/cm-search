#!/usr/bin/env python3
"""
Direct test to see if monitoring is working by making requests
"""
import requests
import time

print("🧪 DIRECT MONITORING TEST")
print("=" * 50)

base_url = "http://localhost:8000"

# Test requests that should trigger monitoring
test_urls = [
    "/company-map/Grid%20Beyond%20Limited/",
    "/technology-map/Battery/", 
    "/api/search-geojson/?tech=Battery&limit=10",
    "/api/map-data/?technology=Battery",
]

print("Making test requests to see if monitoring captures them...")
print("-" * 50)

for url in test_urls:
    print(f"\n📡 Testing: {url}")
    try:
        response = requests.get(f"{base_url}{url}", timeout=10)
        size_kb = len(response.content) / 1024
        print(f"   Response: {response.status_code}, Size: {size_kb:.1f} KB")
        
        # Check if compressed
        encoding = response.headers.get('content-encoding', 'none')
        print(f"   Encoding: {encoding}")
        
    except Exception as e:
        print(f"   Error: {e}")
        
    time.sleep(1)  # Small delay between requests

print(f"\n📊 MONITORING CHECK:")
print("If monitoring is working, you should see:")
print("- [MONITOR] API Call Started messages in the terminal")
print("- [MONITOR] API Call Completed messages")
print("- simple_monitor.py should show these requests")

print(f"\nIf you don't see [MONITOR] messages, the issue is:")
print("1. Monitoring decorator not applied to these endpoints")
print("2. Requests going through different URL patterns")
print("3. Caching preventing function execution")

print(f"\n💡 TRY THIS:")
print("1. Look for [MONITOR] messages in the Django server logs")
print("2. Check if the URLs you click match the test URLs above")
print("3. Use browser dev tools as the most reliable method")