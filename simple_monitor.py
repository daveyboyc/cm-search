#!/usr/bin/env python3
"""
Simple monitoring script - just tracks API calls without loading heavy Django components
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

import time
import datetime

print("🔍 SIMPLE EGRESS MONITOR")
print("=" * 50)
print("Now click on company links and sort pages...")
print("Press Ctrl+C to stop")
print("-" * 50)

try:
    from monitoring.simple_monitor import monitoring_data
    
    last_call_count = 0
    start_time = time.time()
    
    while True:
        current_calls = len(monitoring_data['api_calls'])
        
        # Check for new calls
        if current_calls > last_call_count:
            new_calls = monitoring_data['api_calls'][last_call_count:]
            
            for call in new_calls:
                size_kb = call['size'] / 1024
                timestamp = datetime.datetime.fromtimestamp(call['timestamp']).strftime('%H:%M:%S.%f')[:-3]
                endpoint = call['endpoint']
                
                # Show all calls with size
                if size_kb > 100:
                    print(f"🚨 [{timestamp}] LARGE: {endpoint} = {size_kb:.1f} KB")
                elif size_kb > 50:
                    print(f"⚠️  [{timestamp}] MED: {endpoint} = {size_kb:.1f} KB")
                else:
                    print(f"📡 [{timestamp}] {endpoint} = {size_kb:.1f} KB")
                
                # Show running total
                total_mb = monitoring_data['total_bytes'] / 1024 / 1024
                session_time = time.time() - start_time
                if session_time > 0:
                    hourly_rate = total_mb / (session_time / 3600)
                    monthly_gb = hourly_rate * 24 * 30 / 1024
                    print(f"    📊 Session total: {total_mb:.2f} MB, Monthly proj: {monthly_gb:.2f} GB")
        
        last_call_count = current_calls
        time.sleep(0.5)  # Check every 0.5 seconds
        
except KeyboardInterrupt:
    print(f"\n📋 MONITORING COMPLETE")
    print("=" * 50)
    
    try:
        total_calls = len(monitoring_data['api_calls'])
        total_mb = monitoring_data['total_bytes'] / 1024 / 1024
        session_time = time.time() - start_time
        
        print(f"Session duration: {session_time:.1f} seconds")
        print(f"Total API calls: {total_calls}")
        print(f"Total egress: {total_mb:.2f} MB")
        
        if total_calls > 0:
            print(f"\n📋 ALL CALLS THIS SESSION:")
            for i, call in enumerate(monitoring_data['api_calls'], 1):
                size_kb = call['size'] / 1024
                timestamp = datetime.datetime.fromtimestamp(call['timestamp']).strftime('%H:%M:%S')
                endpoint = call['endpoint']
                print(f"  {i:2d}. [{timestamp}] {endpoint}: {size_kb:.1f} KB")
            
            # Find the largest call
            largest_call = max(monitoring_data['api_calls'], key=lambda x: x['size'])
            largest_kb = largest_call['size'] / 1024
            print(f"\n🎯 LARGEST CALL: {largest_call['endpoint']} = {largest_kb:.1f} KB")
            
            if largest_kb > 200:
                print("🚨 EGRESS SPIKE IDENTIFIED!")
        else:
            print("No API calls detected during monitoring")
            
    except Exception as e:
        print(f"Error in summary: {e}")
        
except Exception as e:
    print(f"❌ Monitoring error: {e}")
    print("The monitoring system may not be properly configured")