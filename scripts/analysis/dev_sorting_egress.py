#!/usr/bin/env python3
"""
Test company-map endpoints and sorting functionality for egress spikes
This simulates the exact actions causing egress jumps
"""
import requests
import json
import time
import urllib.parse

print("🔍 TESTING COMPANY-MAP AND SORTING FOR EGRESS SPIKES")
print("=" * 70)

base_url = "http://localhost:8000"

# Test company-map endpoints with different sorting options
company_tests = [
    {
        'name': 'Company Map - Default',
        'url': f'{base_url}/company-map/Grid%20Beyond%20Limited/',
        'params': {},
        'description': 'Basic company map view'
    },
    {
        'name': 'Company Map - Sort by Location',
        'url': f'{base_url}/company-map/Grid%20Beyond%20Limited/',
        'params': {'sort_by': 'location', 'sort_order': 'asc'},
        'description': 'Sorted by location A-Z'
    },
    {
        'name': 'Company Map - Sort by MW',
        'url': f'{base_url}/company-map/Grid%20Beyond%20Limited/',
        'params': {'sort_by': 'mw', 'sort_order': 'desc'},
        'description': 'Sorted by capacity (highest first)'
    },
    {
        'name': 'Company Map - Sort by Components',
        'url': f'{base_url}/company-map/Grid%20Beyond%20Limited/',
        'params': {'sort_by': 'components', 'sort_order': 'desc'},
        'description': 'Sorted by component count'
    },
    {
        'name': 'Company Map - Active Only',
        'url': f'{base_url}/company-map/Grid%20Beyond%20Limited/',
        'params': {'status': 'active'},
        'description': 'Active locations only'
    },
    {
        'name': 'Company Map - Pagination Page 2',
        'url': f'{base_url}/company-map/Grid%20Beyond%20Limited/',
        'params': {'page': '2'},
        'description': 'Second page of results'
    }
]

# Also test technology map for comparison
tech_tests = [
    {
        'name': 'Technology Map - Battery Default',
        'url': f'{base_url}/technology-map/Battery/',
        'params': {},
        'description': 'Basic technology map view'
    },
    {
        'name': 'Technology Map - Battery Sorted MW',
        'url': f'{base_url}/technology-map/Battery/',
        'params': {'sort_by': 'mw', 'sort_order': 'desc'},
        'description': 'Battery locations sorted by MW'
    }
]

all_tests = company_tests + tech_tests

print(f"🧪 TESTING {len(all_tests)} SCENARIOS:")
print("-" * 70)

results = []
total_size = 0
large_responses = []

for i, test in enumerate(all_tests, 1):
    try:
        print(f"\n📝 {i}. {test['name']}:")
        print(f"   {test['description']}")
        
        start_time = time.time()
        response = requests.get(test['url'], params=test['params'], timeout=30)
        load_time = time.time() - start_time
        
        if response.status_code == 200:
            size_bytes = len(response.content)
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            # Check if compressed
            content_encoding = response.headers.get('content-encoding', 'none')
            
            print(f"   Status: ✅ {response.status_code}")
            print(f"   Size: {size_bytes:,} bytes ({size_kb:.1f} KB)")
            print(f"   Load time: {load_time:.2f}s")
            print(f"   Compression: {content_encoding}")
            
            if size_kb > 200:  # Flag large responses
                print(f"   🚨 LARGE RESPONSE!")
                large_responses.append(test['name'])
            
            total_size += size_bytes
            results.append({
                'name': test['name'],
                'size_kb': size_kb,
                'size_mb': size_mb,
                'load_time': load_time,
                'compressed': content_encoding != 'none',
                'url': test['url'],
                'params': test['params']
            })
            
        else:
            print(f"   Status: ❌ {response.status_code}")
            if response.status_code == 404:
                print(f"   URL: {test['url']}")
                print(f"   (Company might not exist or URL format wrong)")
                
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT - took >30s")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

# Analysis
print(f"\n📊 EGRESS SPIKE ANALYSIS:")
print("=" * 70)
print(f"Total data transferred: {total_size/1024:.1f} KB ({total_size/1024/1024:.2f} MB)")

if large_responses:
    print(f"\n⚠️  LARGE RESPONSES CAUSING SPIKES:")
    for resp_name in large_responses:
        result = next(r for r in results if r['name'] == resp_name)
        print(f"   {resp_name}: {result['size_kb']:.1f} KB")
        print(f"   Compressed: {result['compressed']}")
        if result['params']:
            print(f"   Params: {result['params']}")

# Compare sorting impact
print(f"\n📈 SORTING IMPACT COMPARISON:")
base_company = next((r for r in results if 'Default' in r['name'] and 'Company' in r['name']), None)
if base_company:
    print(f"   Base company map: {base_company['size_kb']:.1f} KB")
    
    for result in results:
        if 'Company Map' in result['name'] and 'Default' not in result['name']:
            diff = result['size_kb'] - base_company['size_kb']
            diff_pct = (diff / base_company['size_kb']) * 100 if base_company['size_kb'] > 0 else 0
            print(f"   {result['name']}: {result['size_kb']:.1f} KB ({diff:+.1f} KB, {diff_pct:+.1f}%)")

# Recommendations
print(f"\n💡 EGRESS SPIKE SOURCES IDENTIFIED:")
print("-" * 70)

if large_responses:
    print("🚨 IMMEDIATE ISSUES:")
    print("   - Large responses found in company-map endpoints")
    print("   - Sorting/filtering may be loading excessive data")
    print("   - Consider adding pagination limits")
else:
    print("✅ GOOD NEWS:")
    print("   - No extremely large responses detected")
    print("   - Optimizations appear to be working")

print(f"\n🎯 RECOMMENDATIONS:")
print("   1. Add stricter pagination limits (max 25 items)")
print("   2. Ensure gzip compression is active on all endpoints")
print("   3. Add longer caching for sorted results")
print("   4. Monitor actual clicks vs these test results")

print(f"\n📋 NEXT STEPS:")
print("   1. Test these exact URLs manually in browser")
print("   2. Check network tab for actual response sizes")
print("   3. Monitor dashboard during manual testing")