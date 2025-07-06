#!/usr/bin/env python
"""
Quick test script to compare both approaches live
"""
import requests
import time

def test_approach(url, name):
    print(f"\n🧪 Testing {name}:")
    print(f"URL: {url}")
    
    start_time = time.time()
    try:
        response = requests.get(url, timeout=10)
        load_time = time.time() - start_time
        
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️  Load time: {load_time:.3f}s")
        print(f"📦 Response size: {len(response.content):,} bytes ({len(response.content)/1024:.1f} KB)")
        
        # Count dropdown options in HTML
        html = response.text
        tech_count = html.count('technology=') - html.count('technology=all')
        company_count = html.count('company=') - html.count('company=all')
        
        print(f"🔍 Technologies in dropdown: ~{tech_count}")
        print(f"🏢 Companies in dropdown: ~{company_count}")
        
        return {
            'load_time': load_time,
            'size_bytes': len(response.content),
            'tech_count': tech_count,
            'company_count': company_count
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    base_url = "http://localhost:8000/search-map/?q=&sort_by=location&sort_order=asc&per_page=25"
    
    print("🔬 LIVE COMPARISON TEST")
    print("=" * 50)
    
    # Test current approach
    current_results = test_approach(base_url, "CURRENT (Sampling)")
    
    # Test O3 approach  
    o3_results = test_approach(base_url + "&use_cached_filters=true", "O3 (Cached)")
    
    if current_results and o3_results:
        print("\n📊 COMPARISON SUMMARY:")
        print("=" * 50)
        
        speed_improvement = current_results['load_time'] / o3_results['load_time']
        size_difference = current_results['size_bytes'] - o3_results['size_bytes']
        tech_improvement = o3_results['tech_count'] - current_results['tech_count']
        company_improvement = o3_results['company_count'] - current_results['company_count']
        
        print(f"🚀 Speed improvement: {speed_improvement:.1f}x faster")
        print(f"📦 Size difference: {size_difference:,} bytes ({size_difference/1024:.1f} KB)")
        print(f"🔧 Technology improvement: +{tech_improvement} options")
        print(f"🏢 Company improvement: +{company_improvement} options")
        
        if speed_improvement > 2 and tech_improvement > 10:
            print("\n✅ O3 APPROACH IS A CLEAR WIN!")
        else:
            print("\n⚠️  Results unclear - check console logs")