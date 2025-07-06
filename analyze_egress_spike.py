#!/usr/bin/env python3
"""
Analysis tool to help identify egress spike patterns
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("🔍 EGRESS SPIKE ANALYSIS TOOL")
print("=" * 60)
print("Based on your feedback about egress jumping from 5% to 15%")
print("when clicking company links and sorting pages...")
print("-" * 60)

# Calculate what 10% egress jump means
print("📊 EGRESS JUMP CALCULATION:")
baseline_5_percent = 5 * 0.01 * 5 * 1024  # 5% of 5GB in MB
jump_15_percent = 15 * 0.01 * 5 * 1024    # 15% of 5GB in MB
difference = jump_15_percent - baseline_5_percent

print(f"  5% of 5GB limit = {baseline_5_percent:.1f} MB")
print(f"  15% of 5GB limit = {jump_15_percent:.1f} MB")
print(f"  Difference = {difference:.1f} MB")
print(f"  That's a {difference*1024:.0f} KB spike!")

# Based on our test results, estimate what could cause this
print(f"\n🎯 POTENTIAL SPIKE SOURCES:")
print(f"  Company-map page: ~97 KB (from our test)")
print(f"  To cause {difference*1024:.0f} KB spike, you'd need:")
print(f"  - {(difference*1024)/97:.0f} company-map page loads, OR")
print(f"  - 1 page with {difference*1024:.0f} KB response, OR")
print(f"  - Multiple API calls totaling {difference*1024:.0f} KB")

# Check what APIs might be called by company-map pages
print(f"\n🔍 COMPANY-MAP PAGE ANALYSIS:")
print(f"Company-map pages typically load:")
print(f"  1. Main HTML page (~97 KB with gzip)")
print(f"  2. CSS/JS assets (usually cached)")
print(f"  3. API calls for dynamic data")
print(f"  4. Map tiles/markers (if Google Maps)")

# Look for potential API endpoints
from checker.urls import urlpatterns
api_patterns = [p for p in urlpatterns if 'api' in str(p.pattern)]

print(f"\n📡 POTENTIAL API ENDPOINTS CALLED BY COMPANY PAGES:")
for pattern in api_patterns:
    pattern_str = str(pattern.pattern)
    if any(keyword in pattern_str for keyword in ['company', 'search', 'map', 'geojson']):
        print(f"  - {pattern_str}")

print(f"\n💡 DEBUGGING STRATEGY:")
print(f"1. IMMEDIATE ACTION:")
print(f"   Run: python monitor_real_time.py")
print(f"   Then click company links while monitoring runs")
print(f"   This will show EXACT endpoints and sizes")

print(f"\n2. BROWSER DEBUGGING:")
print(f"   - Open browser Developer Tools > Network tab")
print(f"   - Click on company link")
print(f"   - Look for large responses in Network tab")
print(f"   - Check if any API calls are >100KB")

print(f"\n3. POTENTIAL ISSUES TO INVESTIGATE:")
print(f"   - /api/search-geojson/ calls without limits")
print(f"   - /api/map-data/ calls loading too much data")
print(f"   - Unoptimized API endpoints")
print(f"   - Missing gzip compression on some responses")
print(f"   - Cache misses causing repeated large calls")

print(f"\n4. SPECIFIC TESTS TO RUN:")
print(f"   A. Test company-map page in incognito (no cache)")
print(f"   B. Try different sorting options")
print(f"   C. Check pagination (page 2, 3, etc.)")
print(f"   D. Compare active vs inactive filtering")

print(f"\n🎯 IMMEDIATE RECOMMENDATION:")
print(f"Run the real-time monitor and click the EXACT company link")
print(f"that caused the 5% → 15% jump. This will show us the culprit!")

# Try to check current monitoring state
try:
    from monitoring.simple_monitor import monitoring_data
    current_calls = len(monitoring_data.get('api_calls', []))
    current_mb = monitoring_data.get('total_bytes', 0) / 1024 / 1024
    
    print(f"\n📊 CURRENT MONITORING STATE:")
    print(f"  API calls logged: {current_calls}")
    print(f"  Total egress: {current_mb:.2f} MB")
    
    if current_calls == 0:
        print(f"  ✅ Monitoring is reset - good time to test!")
    else:
        print(f"  Recent calls detected - monitoring is active")
        
except Exception as e:
    print(f"\n⚠️  Monitoring status: {e}")

print(f"\n" + "=" * 60)
print(f"Ready to debug! Run: python monitor_real_time.py")