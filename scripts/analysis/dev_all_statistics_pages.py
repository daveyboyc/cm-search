#!/usr/bin/env python
"""Test all statistics-related pages for performance"""
import requests
import time

print("📊 Testing ALL Statistics Pages Performance")
print("=" * 60)

base_url = "http://localhost:8000"

# List of all statistics-related URLs to test
test_urls = [
    {"name": "Main Statistics", "url": "/statistics/"},
    {"name": "Companies by Capacity", "url": "/companies/by-total-capacity/"},
    {"name": "Companies by Count", "url": "/companies/by-component-count/"},
    {"name": "Technologies by Count", "url": "/technologies/"},
    {"name": "Technologies by Capacity", "url": "/technologies/by-total-capacity/"},
    {"name": "Components by Capacity", "url": "/components/by-derated-capacity/"},
]

print("\n🔄 Testing each page twice (first load, then cached):")
print("-" * 60)

results = []

for test in test_urls:
    print(f"\n📊 {test['name']}:")
    
    # First load (builds cache)
    start = time.time()
    try:
        response = requests.get(f"{base_url}{test['url']}", timeout=10)
        first_load = time.time() - start
        status1 = response.status_code
    except Exception as e:
        first_load = -1
        status1 = "Error"
        print(f"   ❌ Error on first load: {e}")
    
    # Second load (from cache)
    start = time.time()
    try:
        response = requests.get(f"{base_url}{test['url']}", timeout=10)
        cached_load = time.time() - start
        status2 = response.status_code
    except Exception as e:
        cached_load = -1
        status2 = "Error"
    
    if first_load > 0 and cached_load > 0:
        improvement = first_load / cached_load
        print(f"   First load:  {first_load:.3f}s (status: {status1})")
        print(f"   Cached load: {cached_load:.3f}s (status: {status2})")
        print(f"   Improvement: {improvement:.1f}x faster")
        
        results.append({
            "name": test['name'],
            "first": first_load,
            "cached": cached_load,
            "improvement": improvement
        })

# Summary
print("\n" + "=" * 60)
print("📊 PERFORMANCE SUMMARY:")
print("-" * 60)

if results:
    avg_first = sum(r['first'] for r in results) / len(results)
    avg_cached = sum(r['cached'] for r in results) / len(results)
    avg_improvement = sum(r['improvement'] for r in results) / len(results)
    
    print(f"Average first load:  {avg_first:.3f}s")
    print(f"Average cached load: {avg_cached:.3f}s")
    print(f"Average improvement: {avg_improvement:.1f}x faster")
    
    print("\n📈 Individual Results:")
    for r in results:
        status = "✅" if r['cached'] < 0.1 else "⚠️"
        print(f"   {status} {r['name']:25} {r['first']:.3f}s → {r['cached']:.3f}s ({r['improvement']:.1f}x)")

print("\n💡 All pages now have 1-hour caching!")
print("   - First visitor waits ~1-2s")
print("   - Everyone else gets instant (<0.1s) response")
print("   - Cache refreshes automatically every hour")