"""
Management command to send subscription expiry reminder emails
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from accounts.models import UserProfile
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send subscription expiry reminder emails to users whose subscriptions are about to expire'
    
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
                
                if not profile.has_paid_access or not profile.paid_access_expiry_date:
                    self.stdout.write(self.style.ERROR(f"❌ User {user.email} does not have an active paid subscription"))
                    return
                
                # Calculate time until expiry
                now = timezone.now()
                time_until_expiry = profile.paid_access_expiry_date - now
                minutes_until_expiry = time_until_expiry.total_seconds() / 60
                
                self.stdout.write(f"📧 Sending test subscription expiry reminder to {user.email}")
                self.stdout.write(f"⏱️  Subscription expires in: {minutes_until_expiry:.1f} minutes")
                
                sent = self.send_subscription_expiry_reminder(user, minutes_until_expiry)
                if sent:
                    self.stdout.write(self.style.SUCCESS(f"✅ Test reminder sent to {user.email}"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Failed to send test reminder to {user.email}"))
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ User with email {test_email} not found"))
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ UserProfile not found for {test_email}"))
        else:
            # Check all users for subscription expiry
            users_checked = 0
            reminders_sent = 0
            now = timezone.now()
            
            for user in User.objects.filter(is_active=True):
                try:
                    profile = UserProfile.objects.get(user=user)
                    
                    # Skip users without paid access
                    if not profile.has_paid_access or not profile.paid_access_expiry_date:
                        continue
                    
                    # Check if subscription is about to expire
                    time_until_expiry = profile.paid_access_expiry_date - now
                    minutes_until_expiry = time_until_expiry.total_seconds() / 60
                    
                    users_checked += 1
                    
                    # Send reminder if subscription expires within the specified minutes
                    if 0 < minutes_until_expiry <= minutes_before:
                        self.stdout.write(f"📧 Sending reminder to {user.email} (subscription expires in {minutes_until_expiry:.1f} minutes)")
                        
                        sent = self.send_subscription_expiry_reminder(user, minutes_until_expiry)
                        if sent:
                            reminders_sent += 1
                            self.stdout.write(self.style.SUCCESS(f"✅ Reminder sent to {user.email}"))
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ Failed to send reminder to {user.email}"))
                            
                except UserProfile.DoesNotExist:
                    continue
                    
            self.stdout.write(f"📊 Checked {users_checked} paid users, sent {reminders_sent} reminders")
        
    def send_subscription_expiry_reminder(self, user, minutes_until_expiry):
        """Send subscription expiry reminder email"""
        try:
            # Determine if this is the special testing case
            is_testing = user.email == '5doubow@spamok.com'
            
            if is_testing:
                subject = "🚨 Your Subscription Expires Soon! | Capacity Market Search (Testing)"
                subscription_type = "testing subscription"
            else:
                subject = "🚨 Your Subscription Expires Soon! | Capacity Market Search"
                subscription_type = "£5/year subscription"
            
            # Format remaining time
            if minutes_until_expiry >= 1:
                time_remaining = f"{minutes_until_expiry:.0f} minute{'s' if minutes_until_expiry != 1 else ''}"
            else:
                seconds_remaining = minutes_until_expiry * 60
                time_remaining = f"{seconds_remaining:.0f} second{'s' if seconds_remaining != 1 else ''}"
            
            # Plain text message
            message = f"""Dear {user.username},

🚨 SUBSCRIPTION EXPIRY REMINDER

Your {subscription_type} is about to expire in {time_remaining}!

⏰ What happens when your subscription expires:
• You will lose access to premium features immediately
• No trial period will be available - you'll need to renew to continue
• Your account will remain active but access will be restricted

💡 To continue with unlimited access:
Renew your subscription now for just £5/year:
• Unlimited access to all features
• No time restrictions
• Full interactive map access
• Export capabilities
• Priority support

🔗 Renew now: https://capacitymarket.co.uk/accounts/payment-required/

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
        .urgent {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Subscription Expiry Warning</h1>
        <p>Your subscription is about to expire!</p>
    </div>
    
    <div class="content">
        <p>Dear {user.username},</p>
        
        <div class="warning">
            <h3>⏰ Time Remaining</h3>
            <p class="time-remaining">{time_remaining}</p>
            <p>Your {subscription_type} is about to expire!</p>
        </div>
        
        <div class="urgent">
            <h3>🔒 What happens when your subscription expires:</h3>
            <ul>
                <li><strong>Immediate access loss</strong> to premium features</li>
                <li><strong>No trial period</strong> available - you'll need to renew to continue</li>
                <li><strong>Account remains active</strong> but access will be restricted</li>
            </ul>
        </div>
        
        <div class="features">
            <h3>💡 Renew now to continue unlimited access:</h3>
            <p><strong>Just £5/year for:</strong></p>
            <ul>
                <li>✅ Unlimited access to all features</li>
                <li>✅ No time restrictions</li>
                <li>✅ Full interactive map access</li>
                <li>✅ Export capabilities</li>
                <li>✅ Priority support</li>
            </ul>
        </div>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="https://capacitymarket.co.uk/accounts/payment-required/" class="btn">🔗 Renew Subscription Now</a>
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
            
            logger.info(f"✅ Subscription expiry reminder sent to {user.email} ({time_remaining} remaining)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending subscription expiry reminder to {user.email}: {e}")
            return False