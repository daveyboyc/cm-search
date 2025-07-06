"""
Management command to send trial expiry reminder emails
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send trial expiry reminder emails to users whose trials are about to expire'
    
    def add_arguments(self, parser):
        parser.add_argument('--test-email', type=str, help='Send test reminder to specific email')
        parser.add_argument('--minutes-before', type=int, default=5, help='Minutes before expiry to send reminder')
        
    def handle(self, *args, **options):
        test_email = options.get('test_email')
        minutes_before = options.get('minutes_before', 5)
        
        if test_email:
            # Send test email to specific user
            try:
                user = User.objects.get(email=test_email)
                profile = UserProfile.objects.get(user=user)
                
                # For testing, calculate when to send based on remaining time
                remaining_hours = profile.get_weekly_trial_hours_remaining()
                remaining_minutes = remaining_hours * 60
                
                self.stdout.write(f"📧 Sending test reminder to {user.email}")
                self.stdout.write(f"⏱️  Trial remaining: {remaining_minutes:.1f} minutes")
                
                sent = self.send_trial_expiry_reminder(user, remaining_minutes)
                if sent:
                    self.stdout.write(self.style.SUCCESS(f"✅ Test reminder sent to {user.email}"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Failed to send test reminder to {user.email}"))
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ User with email {test_email} not found"))
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ UserProfile not found for {test_email}"))
        else:
            # Check all users for trial expiry
            users_checked = 0
            reminders_sent = 0
            
            for user in User.objects.filter(is_active=True):
                try:
                    profile = UserProfile.objects.get(user=user)
                    
                    # Skip users with paid access
                    if profile.is_paid_access_active:
                        continue
                    
                    # Check if trial is about to expire
                    remaining_hours = profile.get_weekly_trial_hours_remaining()
                    remaining_minutes = remaining_hours * 60
                    
                    users_checked += 1
                    
                    # Send reminder if trial expires within the specified minutes
                    if 0 < remaining_minutes <= minutes_before:
                        self.stdout.write(f"📧 Sending reminder to {user.email} (trial expires in {remaining_minutes:.1f} minutes)")
                        
                        sent = self.send_trial_expiry_reminder(user, remaining_minutes)
                        if sent:
                            reminders_sent += 1
                            self.stdout.write(self.style.SUCCESS(f"✅ Reminder sent to {user.email}"))
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ Failed to send reminder to {user.email}"))
                            
                except UserProfile.DoesNotExist:
                    continue
                    
            self.stdout.write(f"📊 Checked {users_checked} users, sent {reminders_sent} reminders")
        
    def send_trial_expiry_reminder(self, user, remaining_minutes):
        """Send trial expiry reminder email"""
        try:
            # Determine if this is the special 5-minute testing case
            is_testing = user.email == '5doubow@spamok.com'
            
            if is_testing:
                subject = "🚨 Your 5-Minute Trial Expires Soon! | Capacity Market Search"
                trial_type = "5-minute testing trial"
                reset_info = "Your trial will reset in 5 minutes after expiry for continued testing."
            else:
                subject = "🚨 Your Free Trial Expires Soon! | Capacity Market Search"
                trial_type = "1-week free trial"
                reset_info = "Your trial will reset next month for another week of free access."
            
            # Format remaining time
            if remaining_minutes >= 1:
                time_remaining = f"{remaining_minutes:.0f} minute{'s' if remaining_minutes != 1 else ''}"
            else:
                seconds_remaining = remaining_minutes * 60
                time_remaining = f"{seconds_remaining:.0f} second{'s' if seconds_remaining != 1 else ''}"
            
            # Plain text message
            message = f"""Dear {user.username},

🚨 TRIAL EXPIRY REMINDER

Your {trial_type} is about to expire in {time_remaining}!

⏰ What happens when your trial expires:
• Access to premium features (like the interactive map) will be restricted
• You'll still be able to browse basic information
• {reset_info}

💡 Want to continue with unlimited access?
Upgrade now for just £5/year and get:
• Unlimited access to all features
• No time restrictions
• Full interactive map access
• Export capabilities
• Priority support

🔗 Upgrade now: https://capacitymarket.co.uk/accounts/payment-required/

Thank you for using Capacity Market Search!

Best regards,
Capacity Market Search Team

---
Need help? Reply to this email or visit: https://capacitymarket.co.uk/account/
"""

            # HTML message
            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .features {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; color: #666; }}
        .btn {{ background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
        .time-remaining {{ font-size: 1.5em; font-weight: bold; color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Trial Expiry Warning</h1>
        <p>Your free trial is about to expire!</p>
    </div>
    
    <div class="content">
        <p>Dear {user.username},</p>
        
        <div class="warning">
            <h3>⏰ Time Remaining</h3>
            <p class="time-remaining">{time_remaining}</p>
            <p>Your {trial_type} is about to expire!</p>
        </div>
        
        <h3>🔒 What happens when your trial expires:</h3>
        <ul>
            <li>Access to premium features (like the interactive map) will be restricted</li>
            <li>You'll still be able to browse basic information</li>
            <li>{reset_info}</li>
        </ul>
        
        <div class="features">
            <h3>💡 Want to continue with unlimited access?</h3>
            <p><strong>Upgrade now for just £5/year and get:</strong></p>
            <ul>
                <li>✅ Unlimited access to all features</li>
                <li>✅ No time restrictions</li>
                <li>✅ Full interactive map access</li>
                <li>✅ Export capabilities</li>
                <li>✅ Priority support</li>
            </ul>
        </div>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="https://capacitymarket.co.uk/accounts/payment-required/" class="btn">🔗 Upgrade Now</a>
        </p>
        
        <p>Thank you for using Capacity Market Search!</p>
        
        <p>Best regards,<br>
        <strong>Capacity Market Search Team</strong></p>
    </div>
    
    <div class="footer">
        <p>Need help? Reply to this email or visit: <a href="https://capacitymarket.co.uk/account/">https://capacitymarket.co.uk/account/</a></p>
    </div>
</body>
</html>
"""

            # Send email
            send_mail(
                subject=subject,
                message=message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"✅ Trial expiry reminder sent to {user.email} ({time_remaining} remaining)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending trial expiry reminder to {user.email}: {e}")
            return False