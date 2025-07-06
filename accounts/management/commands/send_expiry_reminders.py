"""
Management command to send expiry reminder emails
Run daily via cron: 0 9 * * * cd /app && python manage.py send_expiry_reminders
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send subscription expiry reminder emails to users'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which emails would be sent without actually sending them'
        )
        parser.add_argument(
            '--days-before',
            type=int,
            default=7,
            help='Send reminder X days before expiry (default: 7)'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_before = options['days_before']
        
        self.stdout.write(f"🔍 Checking for subscriptions expiring in {days_before} days...")
        
        # Calculate target date range (e.g., 7 days from now)
        target_date = timezone.now().date() + timedelta(days=days_before)
        
        # Find users with paid access expiring on target date
        expiring_users = UserProfile.objects.filter(
            has_paid_access=True,
            paid_access_expiry_date__date=target_date
        ).select_related('user')
        
        count = expiring_users.count()
        self.stdout.write(f"📧 Found {count} users with access expiring on {target_date}")
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ No expiry reminders to send today"))
            return
        
        sent_count = 0
        failed_count = 0
        
        for profile in expiring_users:
            user = profile.user
            
            if dry_run:
                self.stdout.write(f"📧 Would send reminder to: {user.email} (expires: {profile.paid_access_expiry_date.date()})")
                continue
            
            try:
                success = self.send_expiry_reminder_email(user, profile.paid_access_expiry_date)
                if success:
                    sent_count += 1
                    self.stdout.write(f"✅ Sent reminder to {user.email}")
                else:
                    failed_count += 1
                    self.stdout.write(f"❌ Failed to send reminder to {user.email}")
                    
            except Exception as e:
                failed_count += 1
                self.stdout.write(f"❌ Error sending reminder to {user.email}: {e}")
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"📊 Summary: {sent_count} sent, {failed_count} failed")
            )
    
    def send_expiry_reminder_email(self, user, expiry_date):
        """Send subscription expiry reminder email"""
        subject = "Subscription Renewal Reminder | Capacity Market Registry"
        
        expiry_str = expiry_date.strftime('%B %d, %Y')
        
        message = f"""Dear {user.username},

🔔 SUBSCRIPTION RENEWAL REMINDER

Your annual subscription to the Capacity Market Registry will expire in 7 days:

📅 Expiry Date: {expiry_str}
💰 Renewal Cost: £5.00/year
🔄 Auto-renewal: Enabled (no action needed)

Your subscription will automatically renew on {expiry_str} for another year. If you wish to cancel, please do so through your Stripe account or contact us.

✅ What you'll continue to have access to:
• Unlimited searches across all technologies
• Full interactive map views with all 63,000+ capacity market components  
• Export functionality for search results
• Company and technology deep-dives
• Latest NESO data updates

🔗 Manage your account: https://capacitymarket.co.uk/account/

Thank you for your continued support!

Best regards,
The Capacity Market Registry Team

---
Need help? Reply to this email or visit: https://capacitymarket.co.uk/account/
"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"✅ Expiry reminder sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending expiry reminder to {user.email}: {e}")
            return False