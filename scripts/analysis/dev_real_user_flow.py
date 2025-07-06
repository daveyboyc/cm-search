#!/usr/bin/env python3
"""
Test real user flow - opening the website and clicking company links
This simulates exactly what you're doing to cause egress spikes
"""
import requests
import time
import json
from urllib.parse import urljoin, quote
import re

print("🔍 TESTING REAL USER FLOW FOR EGRESS SPIKES")
print("=" * 60)

base_url = "http://localhost:8000"
session = requests.Session()

# Track all requests and sizes
all_requests = []
total_egress = 0

def track_request(url, response, description=""):
    global total_egress
    size_bytes = len(response.content)
    size_kb = size_bytes / 1024
    total_egress += size_bytes
    
    encoding = response.headers.get('content-encoding', 'none')
    content_type = response.headers.get('content-type', '')
    
    all_requests.append({
        'url': url,
        'size_kb': size_kb,
        'encoding': encoding,
        'content_type': content_type,
        'description': description
    })
    
    if size_kb > 100:
        print(f"🚨 LARGE: {description}")
        print(f"   URL: {url}")
        print(f"   Size: {size_kb:.1f} KB")
        print(f"   Encoding: {encoding}")
    elif size_kb > 50:
        print(f"⚠️  MED: {description} - {size_kb:.1f} KB")
    else:
        print(f"📡 {description} - {size_kb:.1f} KB")

# Step 1: Load the main page to find company links
print("\n1️⃣ LOADING MAIN PAGE TO FIND COMPANY LINKS")
print("-" * 40)

try:
    # Try common pages that might have company links
    test_pages = [
        "/companies/",
        "/",
        "/companies-premium/",
        "/search-map/"
    ]
    
    company_links = []
    
    for page in test_pages:
        try:
            response = session.get(f"{base_url}{page}", timeout=10)
            track_request(page, response, f"Main page: {page}")
            
            if response.status_code == 200:
                # Look for company-map links in the HTML
                html = response.text
                
                # Find company-map URLs
                company_map_pattern = r'/company-map/([^/\'"]+)/'
                matches = re.findall(company_map_pattern, html)
                
                for match in matches:
                    company_name = match
                    company_url = f"/company-map/{company_name}/"
                    if company_url not in company_links:
                        company_links.append(company_url)
                
                # Also look for regular company links
                company_pattern = r'/company/([^/\'"]+)/'
                matches = re.findall(company_pattern, html)
                
                for match in matches:
                    company_id = match
                    company_url = f"/company/{company_id}/"
                    if company_url not in company_links:
                        company_links.append(company_url)
                        
                print(f"   Found {len(company_links)} company links so far")
                
        except Exception as e:
            print(f"   Error loading {page}: {e}")
    
    print(f"\n📋 FOUND COMPANY LINKS:")
    for i, link in enumerate(company_links[:10], 1):  # Show first 10
        print(f"   {i}. {link}")
    
    if len(company_links) > 10:
        print(f"   ... and {len(company_links) - 10} more")

except Exception as e:
    print(f"❌ Error finding company links: {e}")
    # Fallback to known company links
    company_links = [
        "/company-map/Grid%20Beyond%20Limited/",
        "/company/gridbeyondlimited/",
        "/company-map/Limejump%20Limited/",
    ]
    print(f"Using fallback company links: {company_links}")

# Step 2: Test clicking on company links (the main issue)
print(f"\n2️⃣ TESTING COMPANY LINK CLICKS (MAIN EGRESS SOURCE)")
print("-" * 40)

test_links = company_links[:3]  # Test first 3 links

for i, company_link in enumerate(test_links, 1):
    print(f"\n🔗 Testing company link {i}: {company_link}")
    
    # Clear any caches for this test
    cache_bust = f"?test={int(time.time())}"
    test_url = f"{base_url}{company_link}{cache_bust}"
    
    try:
        response = session.get(test_url, timeout=15)
        track_request(company_link, response, f"Company link {i}")
        
        if response.status_code == 200:
            # Look for additional API calls this page might make
            html = response.text
            
            # Find API endpoints in the HTML/JavaScript
            api_patterns = [
                r'/api/search-geojson/[^"\'\s]*',
                r'/api/map-data/[^"\'\s]*',
                r'/api/component-map-detail/[^"\'\s]*',
                r'/api/company-years/[^"\'\s]*'
            ]
            
            found_apis = []
            for pattern in api_patterns:
                matches = re.findall(pattern, html)
                found_apis.extend(matches)
            
            # Test these API calls that the page would make
            print(f"   Found {len(found_apis)} potential API calls")
            
            for api_url in found_apis[:5]:  # Test first 5 API calls
                try:
                    api_response = session.get(f"{base_url}{api_url}", timeout=10)
                    track_request(api_url, api_response, f"API from company page")
                except Exception as e:
                    print(f"   API error {api_url}: {e}")
                    
    except Exception as e:
        print(f"   ❌ Error loading company link: {e}")

# Step 3: Test sorting (another suspected issue)
print(f"\n3️⃣ TESTING SORTING FUNCTIONALITY")
print("-" * 40)

if company_links:
    base_company_url = company_links[0].split('?')[0]  # Remove any params
    
    sort_tests = [
        "?sort_by=location&sort_order=asc",
        "?sort_by=mw&sort_order=desc", 
        "?sort_by=components&sort_order=desc",
        "?page=2",
        "?status=active",
        "?status=inactive"
    ]
    
    for sort_param in sort_tests:
        test_url = f"{base_url}{base_company_url}{sort_param}"
        print(f"\n🔄 Testing sort: {sort_param}")
        
        try:
            response = session.get(test_url, timeout=10)
            track_request(f"{base_company_url}{sort_param}", response, f"Sort test: {sort_param}")
        except Exception as e:
            print(f"   Error: {e}")

# Step 4: Analysis and Summary
print(f"\n📊 EGRESS SPIKE ANALYSIS")
print("=" * 60)

total_mb = total_egress / 1024 / 1024
print(f"Total egress from this test: {total_mb:.2f} MB")
print(f"Number of requests: {len(all_requests)}")

if all_requests:
    avg_size = sum(r['size_kb'] for r in all_requests) / len(all_requests)
    print(f"Average request size: {avg_size:.1f} KB")
    
    # Find largest requests
    large_requests = [r for r in all_requests if r['size_kb'] > 100]
    if large_requests:
        print(f"\n🚨 LARGE REQUESTS CAUSING EGRESS SPIKES:")
        for req in sorted(large_requests, key=lambda x: x['size_kb'], reverse=True):
            print(f"   {req['description']}: {req['size_kb']:.1f} KB")
            print(f"      URL: {req['url']}")
            print(f"      Encoding: {req['encoding']}")
    
    # Check compression
    uncompressed = [r for r in all_requests if r['encoding'] == 'none' and r['size_kb'] > 20]
    if uncompressed:
        print(f"\n⚠️  UNCOMPRESSED RESPONSES (missing gzip):")
        for req in uncompressed:
            print(f"   {req['description']}: {req['size_kb']:.1f} KB - NO COMPRESSION")
    
    # Estimate monthly impact
    print(f"\n📅 MONTHLY EGRESS PROJECTION:")
    
    # If user does this 20 times per day
    daily_egress = total_mb * 20
    monthly_egress = daily_egress * 30
    
    print(f"   If this flow happens 20x/day: {monthly_egress:.2f} GB/month")
    print(f"   Percentage of 5GB limit: {(monthly_egress/5)*100:.1f}%")
    
    if monthly_egress > 5:
        print(f"   🚨 WOULD EXCEED 5GB LIMIT!")
    elif monthly_egress > 2:
        print(f"   ⚠️  HIGH USAGE - optimization needed")
    else:
        print(f"   ✅ Within reasonable limits")

print(f"\n🎯 RECOMMENDATIONS:")
if large_requests:
    print("   1. CRITICAL: Optimize the large requests identified above")
    print("   2. Add stricter limits to API endpoints")
    print("   3. Implement request-level caching")
else:
    print("   1. Current optimizations appear to be working")
    print("   2. Monitor real usage vs this test")

print(f"\n💡 Next step: Look at the specific large requests above to optimize them further")