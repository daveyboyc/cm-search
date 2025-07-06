#!/usr/bin/env python3
"""
Test script to verify the optimized technology URLs are working correctly.
"""
import os
import sys
import django
import requests
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def test_technology_urls():
    """Test different technology URL patterns."""
    print("🔗 TESTING TECHNOLOGY URL ROUTING")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    technologies = ['DSR', 'Battery', 'Gas', 'Wind', 'Solar']
    
    for tech in technologies:
        print(f"\n🧪 Testing {tech} technology URLs:")
        
        # Test 1: Main technology URL (should redirect to optimized)
        url1 = f"{base_url}/technology/{tech}/"
        try:
            start = time.time()
            response1 = requests.get(url1, allow_redirects=True, timeout=10)
            elapsed1 = time.time() - start
            
            status = "✅" if response1.status_code == 200 else "❌"
            print(f"  {status} /technology/{tech}/: {response1.status_code} - {elapsed1:.3f}s")
            if response1.history:
                print(f"    → Redirected to: {response1.url}")
        except Exception as e:
            print(f"  ❌ /technology/{tech}/: Failed - {e}")
        
        # Test 2: Optimized detail URL
        url2 = f"{base_url}/technology-optimized/{tech}/"
        try:
            start = time.time()
            response2 = requests.get(url2, timeout=10)
            elapsed2 = time.time() - start
            
            status = "✅" if response2.status_code == 200 else "❌"
            print(f"  {status} /technology-optimized/{tech}/: {response2.status_code} - {elapsed2:.3f}s")
        except Exception as e:
            print(f"  ❌ /technology-optimized/{tech}/: Failed - {e}")
        
        # Test 3: Map view URL  
        url3 = f"{base_url}/technology-map/{tech}/"
        try:
            start = time.time()
            response3 = requests.get(url3, timeout=10)
            elapsed3 = time.time() - start
            
            status = "✅" if response3.status_code == 200 else "❌"
            print(f"  {status} /technology-map/{tech}/: {response3.status_code} - {elapsed3:.3f}s")
        except Exception as e:
            print(f"  ❌ /technology-map/{tech}/: Failed - {e}")

def test_performance_comparison():
    """Compare the performance of different URL patterns."""
    print(f"\n🚀 PERFORMANCE COMPARISON")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    tech = "DSR"  # Use DSR since it has the most data
    
    # Test the map view (optimized)
    print(f"\n📊 Testing {tech} performance:")
    
    url_map = f"{base_url}/technology-map/{tech}/"
    try:
        times = []
        for i in range(3):  # Test 3 times
            start = time.time()
            response = requests.get(url_map, timeout=15)
            elapsed = time.time() - start
            times.append(elapsed)
            
            if response.status_code == 200:
                print(f"  ✅ Run {i+1}: {elapsed:.3f}s")
            else:
                print(f"  ❌ Run {i+1}: {response.status_code} - {elapsed:.3f}s")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"\n📈 Average load time: {avg_time:.3f}s")
            print(f"📈 Best time: {min(times):.3f}s")
            print(f"📈 Worst time: {max(times):.3f}s")
            
            if avg_time < 1.0:
                print("🎯 EXCELLENT: Sub-second loading!")
            elif avg_time < 2.0:
                print("✅ GOOD: Fast loading")
            else:
                print("⚠️  SLOW: Still needs optimization")
                
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")

def test_cache_effectiveness():
    """Test if caching is working effectively."""
    print(f"\n💾 TESTING CACHE EFFECTIVENESS")
    print("=" * 50)
    
    from django.core.cache import cache
    
    # Test cache for DSR
    cache_key = "technology_summary_DSR"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        print(f"✅ DSR cache hit: {cached_data['location_count']} locations cached")
        print(f"   Total capacity: {cached_data.get('total_capacity', 0):.1f} MW")
        print(f"   Companies: {len(cached_data.get('companies', []))}")
    else:
        print("❌ DSR cache miss - run: python manage.py optimize_technology_queries --technology DSR")
    
    # Test other technology caches
    other_techs = ['Battery', 'Gas', 'Wind']
    for tech in other_techs:
        cache_key = f"technology_summary_{tech.upper()}"
        cached_data = cache.get(cache_key)
        if cached_data:
            print(f"✅ {tech} cache hit: {cached_data['location_count']} locations")
        else:
            print(f"⚠️  {tech} cache miss")

if __name__ == "__main__":
    test_technology_urls()
    test_performance_comparison() 
    test_cache_effectiveness()
    
    print("\n✅ URL testing complete!")
    print("\nIf all tests pass, your DSR technology page should now load much faster!")
    print("🎯 Next: Visit http://localhost:8000/technology/DSR/ to see the improvements!")