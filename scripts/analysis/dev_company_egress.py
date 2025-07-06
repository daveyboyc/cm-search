#!/usr/bin/env python3
"""
Test company endpoints to identify egress spike source
"""
import requests
import json
import time

print("🔍 TESTING COMPANY ENDPOINTS FOR EGRESS SPIKES")
print("=" * 60)

base_url = "http://localhost:8000"

# Test different company endpoints that could cause spikes
test_cases = [
    {
        'name': 'Company Detail (main page)',
        'url': f'{base_url}/company/gridbeyondlimited/',
        'description': 'Full company detail page with all components'
    },
    {
        'name': 'Company Optimized',
        'url': f'{base_url}/company-optimized/gridbeyondlimited/',
        'description': 'Optimized company view using LocationGroup'
    },
    {
        'name': 'HTMX Company Years',
        'url': f'{base_url}/api/company-years/gridbeyondlimited/2024-25/',
        'description': 'HTMX endpoint for company year details'
    },
    {
        'name': 'Companies List',
        'url': f'{base_url}/companies/',
        'description': 'Full companies list page'
    }
]

print(f"🧪 TESTING ENDPOINTS:")
print("-" * 60)

total_size = 0
results = []

for test in test_cases:
    try:
        print(f"\n📝 {test['name']}:")
        print(f"   {test['description']}")
        
        start_time = time.time()
        response = requests.get(test['url'], timeout=30)
        load_time = time.time() - start_time
        
        if response.status_code == 200:
            size_bytes = len(response.content)
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            print(f"   Status: ✅ {response.status_code}")
            print(f"   Size: {size_bytes:,} bytes ({size_kb:.1f} KB)")
            if size_mb > 1:
                print(f"   ⚠️  LARGE: {size_mb:.2f} MB")
            print(f"   Load time: {load_time:.2f}s")
            
            total_size += size_bytes
            results.append({
                'name': test['name'],
                'size_kb': size_kb,
                'size_mb': size_mb,
                'load_time': load_time,
                'large': size_mb > 1
            })
            
            # Check content type and compression
            content_type = response.headers.get('content-type', '')
            content_encoding = response.headers.get('content-encoding', '')
            print(f"   Content-Type: {content_type}")
            if content_encoding:
                print(f"   Encoding: {content_encoding}")
            else:
                print(f"   Encoding: None (no compression)")
                
        else:
            print(f"   Status: ❌ {response.status_code}")
            if response.status_code == 404:
                print("   (This endpoint might not exist)")
                
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT - endpoint took >30s")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

# Analysis
print(f"\n📊 ANALYSIS:")
print("=" * 60)
print(f"Total data tested: {total_size/1024:.1f} KB ({total_size/1024/1024:.2f} MB)")

# Find the largest responses
large_responses = [r for r in results if r['large']]
if large_responses:
    print(f"\n⚠️  LARGE RESPONSES (>1MB):")
    for resp in large_responses:
        print(f"   {resp['name']}: {resp['size_mb']:.2f} MB")
        
# Find slow responses
slow_responses = [r for r in results if r['load_time'] > 2]
if slow_responses:
    print(f"\n⏱️  SLOW RESPONSES (>2s):")
    for resp in slow_responses:
        print(f"   {resp['name']}: {resp['load_time']:.2f}s")

# Recommendations
print(f"\n💡 RECOMMENDATIONS:")
if large_responses:
    print("   - Large responses found! These could cause egress spikes")
    print("   - Consider adding pagination or limiting data")
    print("   - Ensure gzip compression is working")
else:
    print("   - No large responses detected")
    print("   - Company endpoints appear optimized")

print(f"\n🎯 NEXT STEPS:")
print("   1. Click on a company link in the web interface")
print("   2. Check monitoring dashboard for egress spike")
print("   3. Compare with these baseline measurements")