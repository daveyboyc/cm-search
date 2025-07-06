"""
Start the monitoring daemon for development/production
"""
from monitoring.egress_monitor import start_monitoring_daemon

if __name__ == '__main__':
    print("🚀 Starting egress monitoring daemon...")
    start_monitoring_daemon()
    print("✅ Monitoring daemon started - dashboard available at /monitoring/")
    
    # Keep the script running
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n👋 Monitoring daemon stopped")