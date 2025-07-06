#!/usr/bin/env python3
"""
Test company page performance to see if they need the same optimization as technology pages.
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component, LocationGroup
from django.core.cache import cache

def test_company_performance():
    """Test company query performance."""
    print("🏢 COMPANY QUERY PERFORMANCE TEST")
    print("=" * 60)
    
    # Get some real company names
    companies = Component.objects.values('company_name').annotate(
        component_count=Component.objects.filter(company_name__isnull=False).count()
    ).exclude(company_name__isnull=True).exclude(company_name='')[:5]
    
    print(f"\n📊 Testing {len(companies)} companies...")
    print("-" * 60)
    
    total_old_time = 0
    total_new_time = 0
    
    for i, company_data in enumerate(companies, 1):
        company_name = company_data['company_name']
        if not company_name:
            continue
            
        print(f"\n🔍 Testing {i}. {company_name[:50]}{'...' if len(company_name) > 50 else ''}:")
        
        # Test 1: Old Component-based approach (what main /company/ URLs use)
        start = time.time()
        try:
            old_count = Component.objects.filter(company_name=company_name).count()
            old_time = time.time() - start
            total_old_time += old_time
            
            print(f"  ❌ Component query: {old_time:.3f}s ({old_count:,} components)")
        except Exception as e:
            print(f"  ❌ Component query failed: {e}")
            old_time = 0
            old_count = 0
        
        # Test 2: New LocationGroup approach (what optimized URLs use)
        start = time.time()
        try:
            new_count = LocationGroup.objects.filter(companies__has_key=company_name).count()
            new_time = time.time() - start
            total_new_time += new_time
            
            print(f"  ✅ LocationGroup query: {new_time:.3f}s ({new_count:,} locations)")
        except Exception as e:
            print(f"  ✅ LocationGroup query failed: {e}")
            new_time = 0
            new_count = 0
        
        # Calculate improvement
        if old_time > 0 and new_time > 0:
            improvement = old_time / new_time
            print(f"  📈 Speed improvement: {improvement:.1f}x faster")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPANY PERFORMANCE SUMMARY:")
    print("-" * 60)
    print(f"Total Component query time:    {total_old_time:.3f}s")
    print(f"Total LocationGroup time:      {total_new_time:.3f}s")
    
    if total_old_time > 0 and total_new_time > 0:
        overall_improvement = total_old_time / total_new_time
        print(f"\n🎯 Overall improvement: {overall_improvement:.1f}x faster")
        
        if overall_improvement > 2:
            print("✅ SIGNIFICANT IMPROVEMENT POSSIBLE!")
            print("💡 Company pages should be optimized like technology pages")
        else:
            print("ℹ️  Moderate improvement - optimization optional")

def test_company_url_performance():
    """Test actual company URL performance."""
    print(f"\n🌐 TESTING COMPANY URL PERFORMANCE")
    print("=" * 60)
    
    import requests
    
    # Get a real company name for testing
    company = Component.objects.filter(company_name__isnull=False).first()
    if not company:
        print("❌ No company found for testing")
        return
    
    company_name = company.company_name
    # Normalize for URL
    from checker.utils import normalize
    company_id = normalize(company_name)
    
    base_url = "http://localhost:8000"
    
    print(f"\n🧪 Testing company: {company_name}")
    print(f"   Normalized ID: {company_id}")
    
    # Test different company URLs
    urls_to_test = [
        (f"/company/{company_id}/", "Main company page (slow)"),
        (f"/company-optimized/{company_id}/", "Optimized company page"),
        (f"/company-map/{company_name}/", "Company map view"),
    ]
    
    for url, description in urls_to_test:
        try:
            start = time.time()
            response = requests.get(f"{base_url}{url}", timeout=10)
            elapsed = time.time() - start
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"  {status} {description}: {response.status_code} - {elapsed:.3f}s")
            
        except Exception as e:
            print(f"  ❌ {description}: Failed - {e}")

def check_company_caching():
    """Check if company caching is implemented."""
    print(f"\n💾 CHECKING COMPANY CACHE STATUS")
    print("=" * 60)
    
    # Check if there are any company caches
    cache_patterns = ['company_summary_', 'company_detail_', 'company_map_']
    
    found_caches = 0
    for pattern in cache_patterns:
        # Try a few common company cache keys
        test_keys = [f"{pattern}TEST", f"{pattern}COMPANY"]
        for key in test_keys:
            if cache.get(key):
                found_caches += 1
                print(f"✅ Found cache: {key}")
    
    if found_caches == 0:
        print("❌ No company caches found")
        print("💡 Company caching is not implemented yet")
    else:
        print(f"✅ Found {found_caches} company caches")

if __name__ == "__main__":
    test_company_performance()
    test_company_url_performance()
    check_company_caching()
    
    print(f"\n🎯 CONCLUSION:")
    print("If company queries show significant improvement potential,")
    print("they should get the same optimization treatment as technology pages!")