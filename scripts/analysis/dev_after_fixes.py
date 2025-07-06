#!/usr/bin/env python3
"""
Test the specific pages after our egress fixes
"""
import requests

print("🧪 TESTING AFTER EGRESS FIXES")
print("=" * 50)

base_url = "http://localhost:8000"

# Test the main culprits
test_urls = [
    ("/companies-premium/", "Companies premium (was 1.56 MB)"),
    ("/company-map/OCTOPUS%2520ENERGY%2520LIMITED/", "Company map (was 194 KB)"),
    ("/company-map/FLEXITRICITY%2520LIMITED/", "Company map (was 205 KB)"),
    ("/search-map/", "Search map (was 218 KB)"),
]

print("📊 BEFORE vs AFTER COMPARISON:")
print("-" * 50)

for url, description in test_urls:
    try:
        response = requests.get(f"{base_url}{url}", timeout=10)
        
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            encoding = response.headers.get('content-encoding', 'none')
            
            if size_kb > 200:
                status = "🚨 STILL LARGE"
            elif size_kb > 100:
                status = "⚠️  MEDIUM"
            else:
                status = "✅ GOOD"
            
            print(f"{status} {description}")
            print(f"   Size: {size_kb:.1f} KB")
            print(f"   Compression: {encoding}")
            
            # Calculate improvement for known previous sizes
            if "1.56 MB" in description:
                old_kb = 1564
                improvement = ((old_kb - size_kb) / old_kb) * 100
                print(f"   Improvement: {improvement:.1f}% reduction")
            elif "194 KB" in description or "205 KB" in description:
                old_kb = 200  # Average
                improvement = ((old_kb - size_kb) / old_kb) * 100
                print(f"   Improvement: {improvement:.1f}% reduction")
            elif "218 KB" in description:
                old_kb = 218
                improvement = ((old_kb - size_kb) / old_kb) * 100
                print(f"   Improvement: {improvement:.1f}% reduction")
                
        else:
            print(f"❌ {description}: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ {description}: Error - {e}")
    
    print()

# Test a complete user flow
print("🎯 COMPLETE USER FLOW TEST:")
print("-" * 50)

flow_urls = [
    "/companies-premium/",
    "/company-map/GRIDBEYOND%2520LIMITED/",
    "/company-map/GRIDBEYOND%2520LIMITED/?sort_by=mw&sort_order=desc",
    "/company-map/GRIDBEYOND%2520LIMITED/?page=2",
]

total_flow_kb = 0

for url in flow_urls:
    try:
        response = requests.get(f"{base_url}{url}", timeout=10)
        size_kb = len(response.content) / 1024
        total_flow_kb += size_kb
        print(f"   {url}: {size_kb:.1f} KB")
    except Exception as e:
        print(f"   {url}: Error - {e}")

print(f"\nTotal flow: {total_flow_kb:.1f} KB ({total_flow_kb/1024:.2f} MB)")

# Project monthly usage
daily_flows = 10  # Conservative estimate
monthly_mb = (total_flow_kb / 1024) * daily_flows * 30
monthly_gb = monthly_mb / 1024

print(f"\n📅 MONTHLY PROJECTION:")
print(f"   If you do this flow {daily_flows}x per day:")
print(f"   Monthly usage: {monthly_gb:.2f} GB")
print(f"   Percentage of 5GB limit: {(monthly_gb/5)*100:.1f}%")

if monthly_gb > 5:
    print("   🚨 STILL EXCEEDS 5GB LIMIT")
elif monthly_gb > 2:
    print("   ⚠️  HIGH but manageable")
else:
    print("   ✅ WITHIN SAFE LIMITS")

print(f"\n💡 SUMMARY:")
if total_flow_kb < 200:
    print("   ✅ Excellent - flow under 200KB")
elif total_flow_kb < 500:
    print("   ✅ Good - significant improvement")
else:
    print("   ⚠️  Still needs more optimization")