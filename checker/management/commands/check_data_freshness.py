#!/usr/bin/env python3
"""
Management command to check for new CMU/component data without crawling.
Used for automated monitoring and alerts.

Usage:
    python manage.py check_data_freshness
    python manage.py check_data_freshness --threshold 100 --send-alerts
    python manage.py check_data_freshness --auto-update  # Dangerous - auto-runs full update
"""

import requests
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.mail import send_mail
from django.conf import settings
from checker.models import Component

class Command(BaseCommand):
    help = 'Check for new CMU/component data without crawling'

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=int, default=50, 
                          help='Alert threshold for new CMU IDs (default: 50)')
        parser.add_argument('--send-alerts', action='store_true',
                          help='Send email/Slack alerts if threshold exceeded')
        parser.add_argument('--auto-update', action='store_true',
                          help='Automatically run update pipeline if needed (DANGEROUS)')
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be done without taking action')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== CMR Data Freshness Check ==='))
        
        # Get current status
        status = self.check_data_status()
        
        # Display results
        self.display_status(status)
        
        # Check if action needed
        new_cmus = status['new_cmus']
        new_components = status['new_components']
        
        if new_cmus > options['threshold'] or new_components > 1000:
            self.stdout.write(self.style.WARNING(f'🚨 Update needed: {new_cmus} new CMUs, {new_components} new components'))
            
            if options['send_alerts'] and not options['dry_run']:
                self.send_alerts(status)
                
            if options['auto_update'] and not options['dry_run']:
                self.stdout.write(self.style.ERROR('⚠️  Running auto-update...'))
                # Uncomment when ready to implement
                # call_command('update_database', '--full-pipeline')
                
        else:
            self.stdout.write(self.style.SUCCESS('✅ Data is up to date'))
            
        # Return exit code for scripts
        return 1 if new_cmus > options['threshold'] else 0

    def check_data_status(self):
        """Check API vs database for new data"""
        
        # Check CMU registry totals
        api_cmu_total = self.get_api_cmu_count()
        db_cmu_total = Component.objects.values('cmu_id').distinct().count()
        
        # Check component totals (approximate)
        api_component_total = self.get_api_component_estimate()
        db_component_total = Component.objects.count()
        
        # Get last update timestamp
        last_update = self.get_last_update_time()
        
        return {
            'api_cmus': api_cmu_total,
            'db_cmus': db_cmu_total,
            'new_cmus': api_cmu_total - db_cmu_total,
            'api_components': api_component_total,
            'db_components': db_component_total,
            'new_components': api_component_total - db_component_total,
            'last_update': last_update,
            'check_time': datetime.now()
        }

    def get_api_cmu_count(self):
        """Get total CMU count from API"""
        try:
            url = "https://api.neso.energy/api/3/action/datastore_search"
            params = {
                "resource_id": "25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6",
                "limit": 0
            }
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            return data.get("result", {}).get("total", 0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching API CMU count: {e}'))
            return 0

    def get_api_component_estimate(self):
        """Estimate total components from sample CMUs"""
        try:
            # Sample approach: average components per CMU * total CMUs
            db_avg = Component.objects.count() / max(Component.objects.values('cmu_id').distinct().count(), 1)
            api_cmus = self.get_api_cmu_count()
            return int(db_avg * api_cmus)
        except Exception:
            return 0

    def get_last_update_time(self):
        """Get timestamp of most recent component"""
        try:
            latest = Component.objects.filter(created_at__isnull=False).order_by('-created_at').first()
            return latest.created_at if latest else None
        except Exception:
            return None

    def display_status(self, status):
        """Display status information"""
        self.stdout.write(f"📊 API CMUs: {status['api_cmus']:,}")
        self.stdout.write(f"📊 DB CMUs: {status['db_cmus']:,}")
        self.stdout.write(f"🆕 New CMUs: {status['new_cmus']:,}")
        self.stdout.write(f"📦 API Components (~): {status['api_components']:,}")
        self.stdout.write(f"📦 DB Components: {status['db_components']:,}")
        self.stdout.write(f"🆕 Estimated New Components: {status['new_components']:,}")
        if status['last_update']:
            self.stdout.write(f"🕒 Last Update: {status['last_update']}")

    def send_alerts(self, status):
        """Send alert notifications via Mailgun and Slack"""
        message = f"""
🚨 CMR Data Update Alert

New data detected:
• {status['new_cmus']} new CMU IDs
• ~{status['new_components']} new components

Last update: {status['last_update']}
Check time: {status['check_time']}

Action required: Run data update pipeline
        """
        
        # Send via Mailgun
        try:
            self.send_mailgun_alert(status, message)
            self.stdout.write(self.style.SUCCESS('📧 Mailgun alert sent'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Mailgun failed: {e}'))
        
        # Send via Slack (if configured)
        try:
            self.send_slack_alert(status, message)
            self.stdout.write(self.style.SUCCESS('📱 Slack alert sent'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Slack failed: {e}'))

    def send_mailgun_alert(self, status, message):
        """Send email via Mailgun API"""
        import os
        
        # Mailgun configuration (set via environment variables)
        MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN', 'capacitymarket.co.uk')
        MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
        ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@capacitymarket.co.uk')
        FROM_EMAIL = os.getenv('FROM_EMAIL', 'CMR System <hello@capacitymarket.co.uk>')
        
        if not MAILGUN_API_KEY:
            raise Exception("MAILGUN_API_KEY environment variable not set")
        
        # Prepare HTML email
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">🚨 CMR Data Update Alert</h2>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>New Data Detected:</h3>
                    <ul>
                        <li><strong>{status['new_cmus']}</strong> new CMU IDs</li>
                        <li><strong>~{status['new_components']}</strong> new components</li>
                    </ul>
                </div>
                
                <div style="background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>System Status:</h3>
                    <p><strong>Last Update:</strong> {status['last_update']}</p>
                    <p><strong>Check Time:</strong> {status['check_time']}</p>
                    <p><strong>API CMUs:</strong> {status['api_cmus']:,}</p>
                    <p><strong>DB CMUs:</strong> {status['db_cmus']:,}</p>
                </div>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3>Action Required:</h3>
                    <p>Run the data update pipeline to crawl new components:</p>
                    <code style="background: #f1f1f1; padding: 10px; display: block; border-radius: 3px;">
                        python manage.py crawl_to_database --resume<br>
                        python manage.py geocode_components --limit 1000<br>
                        python manage.py build_location_mapping
                    </code>
                </div>
                
                <hr style="margin: 30px 0;">
                <p style="color: #6c757d; font-size: 0.9em;">
                    This is an automated alert from the CMR monitoring system.<br>
                    Capacity Market Registry Data Pipeline
                </p>
            </div>
        </body>
        </html>
        """
        
        # Send via Mailgun API
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": FROM_EMAIL,
                "to": ADMIN_EMAIL,
                "subject": f"🚨 CMR Alert: {status['new_cmus']} new CMU IDs detected",
                "text": message,
                "html": html_message
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Mailgun API error: {response.status_code} - {response.text}")

    def send_slack_alert(self, status, message):
        """Send alert to Slack via webhook"""
        import os
        
        SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
        if not SLACK_WEBHOOK_URL:
            raise Exception("SLACK_WEBHOOK_URL not configured")
        
        slack_message = {
            "text": "🚨 CMR Data Update Alert",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 CMR Data Update Alert"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*New CMU IDs:*\n{status['new_cmus']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*New Components:*\n~{status['new_components']}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Last Update:* {status['last_update']}\n*Check Time:* {status['check_time']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Action Required:* Run data update pipeline to crawl new components"
                    }
                }
            ]
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_message)
        if response.status_code != 200:
            raise Exception(f"Slack webhook error: {response.status_code}")

    def send_crawl_complete_notification(self, crawl_stats):
        """Send notification when crawl completes successfully"""
        try:
            import os
            
            MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN', 'capacitymarket.co.uk')
            MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
            ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@capacitymarket.co.uk')
            FROM_EMAIL = os.getenv('FROM_EMAIL', 'CMR System <hello@capacitymarket.co.uk>')
            
            if not MAILGUN_API_KEY:
                return
            
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #28a745;">✅ CMR Crawl Complete</h2>
                    
                    <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                        <h3>Crawl Results:</h3>
                        <ul>
                            <li><strong>{crawl_stats.get('components_added', 0)}</strong> new components added</li>
                            <li><strong>{crawl_stats.get('cmu_ids_processed', 0)}</strong> CMU IDs processed</li>
                            <li><strong>{crawl_stats.get('geocoded', 0)}</strong> components geocoded</li>
                        </ul>
                    </div>
                    
                    <p>The CMR database has been successfully updated with the latest data.</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 0.9em;">
                        Automated notification from CMR Data Pipeline
                    </p>
                </div>
            </body>
            </html>
            """
            
            response = requests.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": FROM_EMAIL,
                    "to": ADMIN_EMAIL,
                    "subject": "✅ CMR Data Crawl Complete",
                    "html": html_message
                }
            )
            
        except Exception as e:
            print(f"Failed to send crawl completion notification: {e}")