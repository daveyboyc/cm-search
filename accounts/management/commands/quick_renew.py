"""
Quick renewal command for testing - gives X minute subscriptions
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Quickly renew subscription for X minutes (for testing)'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='5doubow@spamok.com', help='User email')
        parser.add_argument('--minutes', type=int, default=5, help='Minutes until expiry')
        
    def handle(self, *args, **options):
        email = options.get('email')
        minutes = options.get('minutes')
        
        try:
            user = User.objects.get(email=email)
            profile = UserProfile.objects.get(user=user)
            
            # Use subscription manager but override duration for testing
            from accounts.subscription_manager import SubscriptionManager
            profile.has_paid_access = True
            profile.payment_amount = 5.00
            profile.paid_access_expiry_date = timezone.now() + timedelta(minutes=minutes)
            profile.save()
            
            # Log what type this user would normally get
            normal_type = SubscriptionManager.get_subscription_type_display(user.email)
            
            self.stdout.write(self.style.SUCCESS(
                f"✅ RENEWED: {email} now has {minutes}-minute subscription (override)"
            ))
            self.stdout.write(f"   Normal subscription type: {normal_type}")
            self.stdout.write(f"   Expires at: {profile.paid_access_expiry_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            self.stdout.write(f"   Current status: {'ACTIVE' if profile.is_paid_access_active else 'EXPIRED'}")
            
            # Remind about email commands
            self.stdout.write("\n📧 To send emails:")
            self.stdout.write("   Expiry warning: heroku run 'python manage.py send_subscription_expiry_reminders' --app neso-cmr-search")
            self.stdout.write("   After expiry: Run the same command - it will detect expired users")
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User {email} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))