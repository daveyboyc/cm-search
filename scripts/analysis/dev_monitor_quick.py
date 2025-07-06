#!/usr/bin/env python3
"""
Quick test to see if monitoring is working without hanging
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("🔍 QUICK MONITORING TEST")
print("=" * 40)

try:
    from monitoring.simple_monitor import monitoring_data
    
    print(f"✅ Monitoring system accessible")
    print(f"API calls logged: {len(monitoring_data['api_calls'])}")
    print(f"Total bytes: {monitoring_data['total_bytes']}")
    print(f"Endpoint stats: {len(monitoring_data['endpoint_stats'])}")
    
    if monitoring_data['api_calls']:
        print(f"\nRecent calls:")
        for call in monitoring_data['api_calls'][-3:]:
            size_kb = call['size'] / 1024
            print(f"  {call['endpoint']}: {size_kb:.1f} KB")
    else:
        print(f"\nNo API calls logged yet")
        
    print(f"\n✅ Ready for monitoring!")
    print(f"Now you can run: python simple_monitor.py")
    print(f"Or use browser dev tools to see network requests")
    
except ImportError as e:
    print(f"❌ Monitoring not available: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

# Also suggest browser-based debugging
print(f"\n💡 ALTERNATIVE DEBUGGING:")
print(f"1. Open browser Developer Tools > Network tab")
print(f"2. Clear network log")
print(f"3. Click company link")
print(f"4. Look for large responses (>100KB)")
print(f"5. Check response sizes in Size column")
print(f"\nThis will show EXACT requests and sizes causing spikes!")