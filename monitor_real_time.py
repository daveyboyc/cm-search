#!/usr/bin/env python3
"""
Real-time monitoring to catch egress spikes as they happen
Run this while you click on company links and sort pages
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

import time
import datetime

try:
    from monitoring.simple_monitor import monitoring_data
    
    print("🔍 REAL-TIME EGRESS MONITORING")
    print("=" * 60)
    print("Now click on company links and sort pages...")
    print("Press Ctrl+C to stop monitoring")
    print("-" * 60)
    
    # Track previous state
    last_call_count = 0
    last_total_bytes = 0
    
    while True:
        current_calls = len(monitoring_data['api_calls'])
        current_bytes = monitoring_data['total_bytes']
        
        # Check for new calls
        if current_calls > last_call_count:
            new_calls = monitoring_data['api_calls'][last_call_count:]
            
            for call in new_calls:
                size_kb = call['size'] / 1024
                timestamp = datetime.datetime.fromtimestamp(call['timestamp']).strftime('%H:%M:%S')
                endpoint = call['endpoint']
                
                # Highlight large responses
                if size_kb > 50:
                    print(f"🚨 [{timestamp}] LARGE: {endpoint}")
                    print(f"    Size: {size_kb:.1f} KB")
                else:
                    print(f"📡 [{timestamp}] {endpoint}: {size_kb:.1f} KB")
        
        # Update tracking
        last_call_count = current_calls
        
        # Show running totals if changed
        if current_bytes != last_total_bytes:
            total_mb = current_bytes / 1024 / 1024
            runtime = time.time() - monitoring_data['start_time']
            
            if runtime > 0:
                hours_elapsed = runtime / 3600
                mb_per_hour = total_mb / hours_elapsed
                monthly_gb = mb_per_hour * 24 * 30 / 1024
                limit_pct = (monthly_gb / 5) * 100
                
                print(f"📊 Total: {total_mb:.2f} MB, Projection: {monthly_gb:.2f} GB ({limit_pct:.1f}%)")
                
                if limit_pct > 15:
                    print("⚠️  EGRESS SPIKE DETECTED!")
            
            last_total_bytes = current_bytes
        
        time.sleep(1)  # Check every second
        
except KeyboardInterrupt:
    print(f"\n\n📋 FINAL MONITORING SUMMARY:")
    print("=" * 60)
    
    try:
        total_mb = monitoring_data['total_bytes'] / 1024 / 1024
        print(f"Total API calls: {len(monitoring_data['api_calls'])}")
        print(f"Total egress: {total_mb:.2f} MB")
        
        # Show all calls
        if monitoring_data['api_calls']:
            print(f"\n📋 ALL CALLS DURING SESSION:")
            for i, call in enumerate(monitoring_data['api_calls'], 1):
                size_kb = call['size'] / 1024
                timestamp = datetime.datetime.fromtimestamp(call['timestamp']).strftime('%H:%M:%S')
                endpoint = call['endpoint']
                print(f"  {i:2d}. [{timestamp}] {endpoint}: {size_kb:.1f} KB")
        
        # Show endpoint breakdown
        if monitoring_data['endpoint_stats']:
            print(f"\n🎯 ENDPOINT BREAKDOWN:")
            sorted_endpoints = sorted(
                monitoring_data['endpoint_stats'].items(),
                key=lambda x: x[1]['bytes'],
                reverse=True
            )
            
            for endpoint, stats in sorted_endpoints:
                mb = stats['bytes'] / 1024 / 1024
                avg_kb = (stats['bytes'] / stats['calls']) / 1024 if stats['calls'] > 0 else 0
                print(f"  {endpoint}:")
                print(f"    Calls: {stats['calls']}, Total: {mb:.2f} MB, Avg: {avg_kb:.1f} KB")
                
    except Exception as e:
        print(f"Error in summary: {e}")
        
except ImportError:
    print("❌ Monitoring not available")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()