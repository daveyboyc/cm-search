#!/usr/bin/env python3
"""
Test actual response sizes after optimization
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.test import Client
from django.urls import reverse
import json
import sys

client = Client()

print("🔍 TESTING OPTIMIZED RESPONSE SIZES")
print("=" * 50)

# Test the main GeoJSON endpoint
test_cases = [
    {
        'name': 'Battery search (50 results)',
        'url': '/api/search-geojson/',
        'params': {'tech': 'Battery', 'limit': 50}
    },
    {
        'name': 'London search (50 results)',
        'url': '/api/search-geojson/', 
        'params': {'q': 'London', 'limit': 50}
    },
    {
        'name': 'All active locations (100 limit)',
        'url': '/api/search-geojson/',
        'params': {'q': 'energy', 'limit': 100}
    }
]

total_size = 0
for test in test_cases:
    try:
        response = client.get(test['url'], test['params'])
        if response.status_code == 200:
            size_bytes = len(response.content)
            size_kb = size_bytes / 1024
            total_size += size_bytes
            
            # Parse JSON to check data
            data = json.loads(response.content)
            feature_count = len(data.get('features', []))
            
            print(f"\n{test['name']}:")
            print(f"  Status: {response.status_code}")
            print(f"  Size: {size_bytes:,} bytes ({size_kb:.1f} KB)")
            print(f"  Features: {feature_count}")
            
            # Check if we successfully removed the big fields
            if feature_count > 0:
                sample_feature = data['features'][0]['properties']
                removed_fields = ['all_technologies', 'all_companies', 'all_cmu_ids', 'all_years']
                has_removed = any(field in sample_feature for field in removed_fields)
                print(f"  Optimization: {'❌ Still has removed fields!' if has_removed else '✅ Fields removed'}")
                
                # Show remaining fields
                fields = list(sample_feature.keys())
                print(f"  Fields: {', '.join(fields[:8])}{'...' if len(fields) > 8 else ''}")
        else:
            print(f"\n{test['name']}: ❌ Error {response.status_code}")
    except Exception as e:
        print(f"\n{test['name']}: ❌ Error: {e}")

print(f"\n📊 SUMMARY:")
print(f"Total test data: {total_size:,} bytes ({total_size/1024:.1f} KB)")

# Estimate compression
import gzip
from io import BytesIO
if total_size > 0:
    # Simulate gzip compression
    test_content = b'x' * total_size  # Approximate
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
        f.write(test_content)
    compressed_size = len(buffer.getvalue())
    compression_ratio = (1 - compressed_size/total_size) * 100
    
    print(f"Estimated with gzip: {compressed_size:,} bytes ({compression_ratio:.1f}% reduction)")

print(f"\n💡 Check the monitoring dashboard for real usage data after testing some searches.")