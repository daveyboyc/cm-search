# Add this to your Django app's ready() method or manage.py

from monitoring.egress_monitor import start_monitoring_daemon

# Start the monitoring daemon
start_monitoring_daemon()
print("🚀 Egress monitoring daemon started")