#!/usr/bin/env python3
"""
Test real clicking behavior - multiple company-map, technology-map, and sorting
Simulates exactly what you're doing to get to 26% egress
"""
import requests
import time
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("🔍 TESTING REAL CLICKING BEHAVIOR")
print("=" * 60)

base_url = "http://localhost:8000"
session = requests.Session()

# Track egress in real time
total_egress = 0
request_count = 0

def make_request(url, description):
    global total_egress, request_count
    
    try:
        print(f"\n📡 {description}")
        print(f"   URL: {url}")
        
        start_time = time.time()
        response = session.get(url, timeout=15)
        load_time = time.time() - start_time
        
        if response.status_code == 200:
            size_bytes = len(response.content)
            size_kb = size_bytes / 1024
            total_egress += size_bytes
            request_count += 1
            
            encoding = response.headers.get('content-encoding', 'none')
            
            # Calculate running totals
            total_mb = total_egress / 1024 / 1024
            
            # Estimate monthly projection
            if request_count > 0:
                avg_per_request = total_mb / request_count
                # If user makes 50 requests per day (reasonable for testing/usage)
                daily_mb = avg_per_request * 50
                monthly_gb = daily_mb * 30 / 1024
                limit_pct = (monthly_gb / 5) * 100
            else:
                limit_pct = 0
            
            status = "🚨 LARGE" if size_kb > 150 else "⚠️ MED" if size_kb > 75 else "✅ OK"
            
            print(f"   {status} Size: {size_kb:.1f} KB, Time: {load_time:.1f}s, Encoding: {encoding}")
            print(f"   📊 Running total: {total_mb:.2f} MB ({request_count} requests)")
            print(f"   📈 Monthly projection: {monthly_gb:.2f} GB ({limit_pct:.1f}% of 5GB limit)")
            
            if limit_pct > 100:
                print(f"   🚨 WOULD EXCEED LIMIT!")
            elif limit_pct > 50:
                print(f"   ⚠️ HIGH USAGE")
            
        else:
            print(f"   ❌ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Simulate real user clicking behavior
print("🎯 SIMULATING REAL USER CLICKING BEHAVIOR")
print("-" * 60)

# 1. Start at companies page
make_request(f"{base_url}/companies-premium/", "1. Load companies list")

# 2. Click on a few company-map links
companies = [
    "GRIDBEYOND%2520LIMITED",
    "FLEXITRICITY%2520LIMITED", 
    "OCTOPUS%2520ENERGY%2520LIMITED",
    "ENEL%2520X%2520UK%2520LIMITED"
]

for i, company in enumerate(companies, 2):
    make_request(f"{base_url}/company-map/{company}/", f"{i}. Click company-map: {company.replace('%2520', ' ')}")

# 3. Try sorting on a company page
company = companies[0]
sorts = [
    "sort_by=location&sort_order=asc",
    "sort_by=mw&sort_order=desc", 
    "sort_by=components&sort_order=desc"
]

for i, sort_param in enumerate(sorts, 6):
    make_request(f"{base_url}/company-map/{company}/?{sort_param}", f"{i}. Sort company page: {sort_param}")

# 4. Try pagination
make_request(f"{base_url}/company-map/{company}/?page=2", "9. Company page 2")
make_request(f"{base_url}/company-map/{company}/?page=3", "10. Company page 3")

# 5. Test technology-map links
technologies = [
    "Battery",
    "Solar", 
    "Wind",
    "Gas"
]

for i, tech in enumerate(technologies, 11):
    make_request(f"{base_url}/technology-map/{tech}/", f"{i}. Click technology-map: {tech}")

# 6. Sort technology pages
tech = technologies[0]
for i, sort_param in enumerate(sorts, 15):
    make_request(f"{base_url}/technology-map/{tech}/?{sort_param}", f"{i}. Sort technology page: {sort_param}")

# 7. Technology pagination
make_request(f"{base_url}/technology-map/{tech}/?page=2", "18. Technology page 2")

# 8. Test status filtering
filters = [
    "status=active",
    "status=inactive"
]

for i, filter_param in enumerate(filters, 19):
    make_request(f"{base_url}/company-map/{company}/?{filter_param}", f"{i}. Filter company: {filter_param}")
    make_request(f"{base_url}/technology-map/{tech}/?{filter_param}", f"{i+0.5}. Filter technology: {filter_param}")

print(f"\n" + "="*60)
print("📊 FINAL EGRESS ANALYSIS")
print("="*60)

final_mb = total_egress / 1024 / 1024
print(f"Total requests made: {request_count}")
print(f"Total egress: {final_mb:.2f} MB")

if request_count > 0:
    avg_per_request = final_mb / request_count
    print(f"Average per request: {avg_per_request:.2f} MB")
    
    # Project for different usage levels
    usage_scenarios = [
        (10, "Light usage (10 clicks/day)"),
        (25, "Medium usage (25 clicks/day)"), 
        (50, "Heavy usage (50 clicks/day)"),
        (100, "Very heavy usage (100 clicks/day)")
    ]
    
    print(f"\n📅 MONTHLY PROJECTIONS:")
    for daily_clicks, scenario in usage_scenarios:
        daily_mb = avg_per_request * daily_clicks
        monthly_gb = daily_mb * 30 / 1024
        limit_pct = (monthly_gb / 5) * 100
        
        status = "🚨" if limit_pct > 100 else "⚠️" if limit_pct > 50 else "✅"
        print(f"   {status} {scenario}: {monthly_gb:.2f} GB ({limit_pct:.1f}% of limit)")

# Check if monitoring captured this
try:
    from monitoring.simple_monitor import monitoring_data
    monitored_calls = len(monitoring_data['api_calls'])
    monitored_mb = monitoring_data['total_bytes'] / 1024 / 1024
    
    print(f"\n🔍 MONITORING SYSTEM CHECK:")
    print(f"   Requests captured by monitoring: {monitored_calls}")
    print(f"   Egress captured by monitoring: {monitored_mb:.2f} MB")
    
    if monitored_calls < request_count:
        print(f"   ⚠️ Monitoring missing {request_count - monitored_calls} requests")
        print(f"   This suggests some endpoints aren't being monitored")
    else:
        print(f"   ✅ Monitoring is capturing all requests")
        
except Exception as e:
    print(f"\n⚠️ Monitoring system error: {e}")

print(f"\n💡 RECOMMENDATIONS:")
if final_mb > 10:
    print("   🚨 CRITICAL: Still generating massive egress")
    print("   - Need more aggressive pagination (5 items per page)")
    print("   - Consider removing heavy content from pages")
    print("   - Implement lazy loading")
elif final_mb > 5:
    print("   ⚠️ HIGH: Significant egress usage")
    print("   - Consider reducing page content further")
    print("   - Add more caching")
else:
    print("   ✅ GOOD: Reasonable egress usage")
    print("   - Current optimizations working well")

print(f"\n🎯 NEXT STEPS:")
print("   1. Identify the largest individual responses above")
print("   2. Focus optimization on those specific endpoints")
print("   3. Consider template-level optimizations")
print("   4. Test with browser dev tools for exact measurements")