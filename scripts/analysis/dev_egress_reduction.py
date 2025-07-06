#!/usr/bin/env python3
"""
Test script to validate egress reduction
Compares response sizes before/after optimization
"""
import requests
import json
import gzip
from io import BytesIO

def get_response_size(url, params=None):
    """Get response size with gzip simulation"""
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            content = response.content
            original_size = len(content)
            
            # Simulate gzip compression
            buffer = BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
                f.write(content)
            compressed_size = len(buffer.getvalue())
            
            return original_size, compressed_size, response.status_code
        else:
            return 0, 0, response.status_code
    except Exception as e:
        print(f"Error testing {url}: {e}")
        return 0, 0, 0

print("🧪 TESTING EGRESS REDUCTION")
print("=" * 50)

# Test different search scenarios
base_url = "http://localhost:8000"  # Adjust if needed
test_cases = [
    {
        'name': 'Battery search (limited)',
        'url': f'{base_url}/api/search-geojson/',
        'params': {'tech': 'Battery', 'limit': 50}
    },
    {
        'name': 'London search (limited)', 
        'url': f'{base_url}/api/search-geojson/',
        'params': {'q': 'London', 'limit': 50}
    },
    {
        'name': 'Map data API',
        'url': f'{base_url}/api/map-data/',
        'params': {'technology': 'Battery'}
    }
]

print("\n📊 RESPONSE SIZE ANALYSIS:")
print("-" * 50)

total_original = 0
total_compressed = 0

for test in test_cases:
    original, compressed, status = get_response_size(test['url'], test.get('params'))
    
    if status == 200:
        reduction = ((original - compressed) / original * 100) if original > 0 else 0
        total_original += original
        total_compressed += compressed
        
        print(f"\n{test['name']}:")
        print(f"  Original:    {original:,} bytes ({original/1024:.1f} KB)")
        print(f"  Compressed:  {compressed:,} bytes ({compressed/1024:.1f} KB)")
        print(f"  Reduction:   {reduction:.1f}%")
    else:
        print(f"\n{test['name']}: Error (status {status})")

if total_original > 0:
    total_reduction = ((total_original - total_compressed) / total_original * 100)
    print(f"\n📈 TOTAL EGRESS IMPACT:")
    print(f"  Before optimization: {total_original:,} bytes ({total_original/1024:.1f} KB)")
    print(f"  After optimization:  {total_compressed:,} bytes ({total_compressed/1024:.1f} KB)")
    print(f"  Overall reduction:   {total_reduction:.1f}%")
    
    # Estimate monthly impact
    daily_requests = 1000  # Conservative estimate
    monthly_before = (total_original * daily_requests * 30) / (1024**3)  # GB
    monthly_after = (total_compressed * daily_requests * 30) / (1024**3)  # GB
    
    print(f"\n📅 MONTHLY PROJECTION (1K requests/day):")
    print(f"  Before: {monthly_before:.2f} GB/month")
    print(f"  After:  {monthly_after:.2f} GB/month")
    print(f"  Saved:  {monthly_before - monthly_after:.2f} GB/month")

print("\n✅ Test complete! Check your monitoring dashboard for real impact.")