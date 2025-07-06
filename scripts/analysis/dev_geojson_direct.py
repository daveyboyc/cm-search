#!/usr/bin/env python3
"""
Test the GeoJSON endpoint directly to check optimization
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.views_search_geojson import search_results_geojson
from django.http import HttpRequest
import json

print("🔍 TESTING GEOJSON OPTIMIZATION DIRECTLY")
print("=" * 50)

# Create a mock request
request = HttpRequest()
request.method = 'GET'
request.GET = {'tech': 'Battery', 'limit': '10'}  # Small test

try:
    response = search_results_geojson(request)
    
    if hasattr(response, 'content'):
        content = response.content.decode('utf-8')
        data = json.loads(content)
        
        size_bytes = len(content)
        size_kb = size_bytes / 1024
        
        print(f"✅ Response generated successfully")
        print(f"📊 Size: {size_bytes:,} bytes ({size_kb:.1f} KB)")
        print(f"🔢 Features: {len(data.get('features', []))}")
        
        # Check if optimization worked
        if data.get('features'):
            sample = data['features'][0]['properties']
            removed_fields = ['all_technologies', 'all_companies', 'all_cmu_ids', 'all_years']
            
            print(f"\n🔍 OPTIMIZATION CHECK:")
            for field in removed_fields:
                status = "❌ STILL PRESENT" if field in sample else "✅ REMOVED"
                print(f"  {field}: {status}")
            
            print(f"\n📝 REMAINING FIELDS ({len(sample)} total):")
            for field in sorted(sample.keys()):
                print(f"  - {field}")
                
            # Estimate size per feature
            avg_size = size_bytes / len(data['features'])
            print(f"\n📈 EFFICIENCY:")
            print(f"  - Avg per feature: {avg_size:.0f} bytes")
            print(f"  - For 100 features: {avg_size * 100 / 1024:.1f} KB")
            print(f"  - For 250 features: {avg_size * 250 / 1024:.1f} KB")
        
        print(f"\n📋 METADATA:")
        meta = data.get('metadata', {})
        for key, value in meta.items():
            print(f"  {key}: {value}")
            
    else:
        print(f"❌ Unexpected response type: {type(response)}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()