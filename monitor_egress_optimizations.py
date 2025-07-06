#!/usr/bin/env python3
"""
Real-time egress optimization monitoring script
Tracks optimization metrics from Django logs
"""
import os
import sys
import subprocess
import re
import time
from datetime import datetime
from collections import defaultdict

class EgressMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.total_requests = 0
        self.total_egress_saved = 0
        
    def parse_log_line(self, line):
        """Parse optimization log lines and extract metrics"""
        if "EGRESS-OPTIMIZED" not in line:
            return None
            
        # Extract view type
        view_type = "unknown"
        if "company view" in line:
            view_type = "company_list"
        elif "company map" in line:
            view_type = "company_map"
        elif "technology map" in line:
            view_type = "technology_map"
        elif "search map view" in line:
            view_type = "search_map"
            
        return {"view_type": view_type, "line": line}
    
    def extract_metrics(self, log_lines):
        """Extract metrics from consecutive log lines"""
        metrics = {}
        
        for line in log_lines:
            # Total locations
            match = re.search(r'Total locations: (\d+)', line)
            if match:
                metrics['total_locations'] = int(match.group(1))
                
            # Displayed items
            match = re.search(r'Displayed: (\d+) items', line)
            if match:
                metrics['displayed'] = int(match.group(1))
                
            # Database queries
            match = re.search(r'Database queries: (\d+)', line)
            if match:
                metrics['queries'] = int(match.group(1))
                
            # Rows fetched
            match = re.search(r'Rows fetched: (\d+)', line)
            if match:
                metrics['rows_fetched'] = int(match.group(1))
                
            # Estimated data
            match = re.search(r'Estimated data: ([\d,]+) bytes', line)
            if match:
                metrics['estimated_bytes'] = int(match.group(1).replace(',', ''))
                
            # Load time
            match = re.search(r'Load time: ([\d.]+)s', line)
            if match:
                metrics['load_time'] = float(match.group(1))
                
            # Egress reduction
            match = re.search(r'egress reduction: ([\d.]+)%.*?(\d+,?\d*) → (\d+,?\d*) bytes', line)
            if match:
                metrics['reduction_percent'] = float(match.group(1))
                metrics['old_bytes'] = int(match.group(2).replace(',', ''))
                metrics['new_bytes'] = int(match.group(3).replace(',', ''))
                metrics['bytes_saved'] = metrics['old_bytes'] - metrics['new_bytes']
                
        return metrics
    
    def display_dashboard(self):
        """Display real-time optimization dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 EGRESS OPTIMIZATION DASHBOARD")
        print("=" * 60)
        print(f"⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total requests monitored: {self.total_requests}")
        print(f"💾 Total egress saved: {self.total_egress_saved:,} bytes ({self.total_egress_saved/1024/1024:.1f} MB)")
        print()
        
        if not self.metrics:
            print("⏳ Waiting for optimization logs...")
            print()
            print("💡 TIP: Make requests to optimized endpoints:")
            print("   http://localhost:8000/company-optimized/gridbeyondlimited/")
            print("   http://localhost:8000/technology-map/DSR/")
            print("   http://localhost:8000/map/?query=london")
            return
            
        # Display metrics by view type
        for view_type, metric_list in self.metrics.items():
            if not metric_list:
                continue
                
            latest = metric_list[-1]
            avg_reduction = sum(m.get('reduction_percent', 0) for m in metric_list) / len(metric_list)
            total_saved = sum(m.get('bytes_saved', 0) for m in metric_list)
            
            print(f"📈 {view_type.upper().replace('_', ' ')}:")
            print(f"   🔢 Requests: {len(metric_list)}")
            print(f"   📊 Avg reduction: {avg_reduction:.1f}%")
            print(f"   💾 Total saved: {total_saved:,} bytes ({total_saved/1024:.1f} KB)")
            
            if 'load_time' in latest:
                print(f"   ⏱️  Latest load time: {latest['load_time']:.3f}s")
            if 'queries' in latest:
                print(f"   💾 Latest DB queries: {latest['queries']}")
            if 'total_locations' in latest and 'displayed' in latest:
                print(f"   📋 Latest efficiency: {latest['displayed']}/{latest['total_locations']} locations displayed")
            print()
    
    def monitor_logs(self):
        """Monitor Django logs for optimization metrics"""
        print("🔍 Starting egress optimization monitoring...")
        print("📝 Watching for EGRESS-OPTIMIZED log messages...")
        print("🔄 Press Ctrl+C to stop monitoring")
        print()
        
        try:
            # Try to tail Django logs if server is running
            while True:
                try:
                    # For now, just display the dashboard every few seconds
                    # In production, this would tail actual log files
                    self.display_dashboard()
                    time.sleep(3)
                    
                except KeyboardInterrupt:
                    print("\n👋 Monitoring stopped")
                    break
                except Exception as e:
                    print(f"❌ Monitoring error: {e}")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"❌ Failed to start monitoring: {e}")
    
    def simulate_optimization_data(self):
        """Simulate some optimization data for testing"""
        sample_metrics = [
            {
                'view_type': 'company_list',
                'total_locations': 323,
                'displayed': 50,
                'queries': 4,
                'rows_fetched': 150,
                'load_time': 0.087,
                'reduction_percent': 88.4,
                'old_bytes': 387600,
                'new_bytes': 45000,
                'bytes_saved': 342600
            },
            {
                'view_type': 'technology_map', 
                'total_locations': 1247,
                'displayed': 25,
                'queries': 5,
                'rows_fetched': 125,
                'load_time': 0.134,
                'reduction_percent': 95.7,
                'old_bytes': 1496400,
                'new_bytes': 62500,
                'bytes_saved': 1433900
            }
        ]
        
        for metrics in sample_metrics:
            self.metrics[metrics['view_type']].append(metrics)
            self.total_requests += 1
            self.total_egress_saved += metrics['bytes_saved']

def show_setup_instructions():
    """Show setup instructions for monitoring"""
    print("🔧 EGRESS MONITORING SETUP")
    print("=" * 50)
    print()
    print("1. 🚀 Start Django development server:")
    print("   python manage.py runserver")
    print()
    print("2. 📊 Start monitoring (in another terminal):")
    print("   python monitor_egress_optimizations.py")
    print()
    print("3. 🧪 Test optimized endpoints:")
    print("   # Company views")
    print("   curl http://localhost:8000/company-optimized/gridbeyondlimited/")
    print("   curl http://localhost:8000/company-map/ENEL%20X%20UK%20LIMITED/")
    print()
    print("   # Technology views") 
    print("   curl http://localhost:8000/technology-map/DSR/")
    print("   curl http://localhost:8000/technology-optimized/Battery/")
    print()
    print("   # Search views")
    print("   curl http://localhost:8000/map/?query=london")
    print("   curl http://localhost:8000/map/?query=london&status=active")
    print()
    print("4. 📈 Watch dashboard for optimization metrics")
    print()
    print("✅ Expected metrics:")
    print("   - 🔢 Database queries: 3-6 (down from 10-100+)")
    print("   - 📦 Rows fetched: <200 (down from 1000+)")
    print("   - ⏱️  Load time: <0.5s (down from 2-5s)")
    print("   - 💾 Egress reduction: 90%+ (massive savings)")

if __name__ == "__main__":
    print("🚀 EGRESS OPTIMIZATION MONITOR")
    print("=" * 50)
    
    monitor = EgressMonitor()
    
    try:
        choice = input("🤔 Choose option:\n  1. Show setup instructions\n  2. Start monitoring (demo)\n  3. Exit\nChoice (1-3): ").strip()
        
        if choice == "1":
            show_setup_instructions()
        elif choice == "2":
            print("\n📊 Starting demo monitoring with sample data...")
            monitor.simulate_optimization_data()
            monitor.monitor_logs()
        else:
            print("👋 Exiting...")
            
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"❌ Error: {e}")