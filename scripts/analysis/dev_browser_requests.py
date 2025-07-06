#!/usr/bin/env python3
"""
Test to find all the additional requests a browser would make
when loading company-map and technology-map pages
"""
import requests
import re
from urllib.parse import urljoin, urlparse

print("🔍 TESTING BROWSER-LIKE REQUEST PATTERNS")
print("=" * 60)

base_url = "http://localhost:8000"
session = requests.Session()

def extract_resources_from_html(html, base_url):
    """Extract all resources a browser would load from HTML"""
    resources = []
    
    # Find CSS files
    css_pattern = r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']'
    css_matches = re.findall(css_pattern, html, re.IGNORECASE)
    resources.extend([('CSS', url) for url in css_matches])
    
    # Find JS files
    js_pattern = r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']'
    js_matches = re.findall(js_pattern, html, re.IGNORECASE)
    resources.extend([('JS', url) for url in js_matches])
    
    # Find API calls in JavaScript
    api_patterns = [
        r'["\'](/api/[^"\']+)["\']',
        r'url:\s*["\']([^"\']+/api/[^"\']*)["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'\.get\(["\']([^"\']+)["\']',
        r'ajax\(["\']([^"\']+)["\']'
    ]
    
    for pattern in api_patterns:
        api_matches = re.findall(pattern, html, re.IGNORECASE)
        resources.extend([('API', url) for url in api_matches])
    
    # Find image references
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    img_matches = re.findall(img_pattern, html, re.IGNORECASE)
    resources.extend([('IMG', url) for url in img_matches])
    
    return resources

def test_page_resources(url, description):
    """Test all resources a page would load"""
    print(f"\n🌐 TESTING: {description}")
    print(f"   URL: {url}")
    
    total_egress = 0
    resource_count = 0
    
    try:
        # Load main page
        response = session.get(url, timeout=10)
        main_size = len(response.content)
        total_egress += main_size
        resource_count += 1
        
        print(f"   📄 Main page: {main_size/1024:.1f} KB")
        
        if response.status_code == 200:
            # Extract all resources
            resources = extract_resources_from_html(response.text, base_url)
            
            print(f"   📦 Found {len(resources)} additional resources:")
            
            # Test each resource
            for resource_type, resource_url in resources[:10]:  # Limit to first 10
                try:
                    # Make URL absolute
                    if resource_url.startswith('/'):
                        full_url = base_url + resource_url
                    elif resource_url.startswith('http'):
                        full_url = resource_url
                    else:
                        full_url = urljoin(url, resource_url)
                    
                    # Skip external URLs
                    if urlparse(full_url).netloc and urlparse(full_url).netloc != urlparse(base_url).netloc:
                        continue
                    
                    resource_response = session.get(full_url, timeout=5)
                    resource_size = len(resource_response.content)
                    total_egress += resource_size
                    resource_count += 1
                    
                    if resource_size > 1024:  # Show resources > 1KB
                        print(f"      {resource_type}: {resource_url} - {resource_size/1024:.1f} KB")
                    
                except Exception as e:
                    print(f"      {resource_type}: {resource_url} - Error: {e}")
                    
        print(f"   📊 Total with resources: {total_egress/1024:.1f} KB ({resource_count} requests)")
        return total_egress
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0

# Test the pages that are causing 26% egress
test_urls = [
    (f"{base_url}/company-map/GRIDBEYOND%2520LIMITED/", "Company map page"),
    (f"{base_url}/technology-map/Battery/", "Technology map page"),
    (f"{base_url}/companies-premium/", "Companies premium page"),
    (f"{base_url}/search-map/", "Search map page")
]

total_session_egress = 0

for url, description in test_urls:
    page_egress = test_page_resources(url, description)
    total_session_egress += page_egress

print(f"\n" + "="*60)
print("📊 COMPLETE BROWSER SESSION ANALYSIS")
print("="*60)

session_mb = total_session_egress / 1024 / 1024
print(f"Total egress (including all resources): {session_mb:.2f} MB")

# Calculate what this means for monthly usage
scenarios = [
    (5, "Light usage (5 sessions/day)"),
    (10, "Medium usage (10 sessions/day)"),
    (20, "Heavy usage (20 sessions/day)")
]

print(f"\n📅 MONTHLY PROJECTIONS WITH ALL RESOURCES:")
for daily_sessions, scenario in scenarios:
    monthly_gb = (session_mb * daily_sessions * 30) / 1024
    limit_pct = (monthly_gb / 5) * 100
    
    status = "🚨" if limit_pct > 100 else "⚠️" if limit_pct > 50 else "✅"
    print(f"   {status} {scenario}: {monthly_gb:.2f} GB ({limit_pct:.1f}% of limit)")

print(f"\n🎯 ANALYSIS:")
if session_mb > 10:
    print("   🚨 FOUND THE PROBLEM: Additional resources are massive")
    print("   - Static files (CSS/JS) might be too large")
    print("   - API calls loading too much data")
    print("   - Need to optimize static assets")
elif session_mb > 5:
    print("   ⚠️ MODERATE ISSUE: Some additional overhead")
    print("   - Check for large API calls")
    print("   - Consider minifying static files")
else:
    print("   ✅ REASONABLE: Additional resources are normal")
    print("   - Issue might be elsewhere")

print(f"\n💡 RECOMMENDATIONS:")
print("   1. Check browser dev tools for actual network usage")
print("   2. Look for large CSS/JS files")
print("   3. Check for repeated API calls")
print("   4. Monitor actual vs simulated usage")