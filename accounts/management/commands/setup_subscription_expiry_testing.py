"""
Management command to set up subscription expiry testing for 5doubow@spamok.com
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Set up subscription expiry testing for 5doubow@spamok.com'
    
    def add_arguments(self, parser):
        parser.add_argument('--expire-in-5min', action='store_true', help='Set subscription to expire in 5 minutes')
        parser.add_argument('--expire-in-2min', action='store_true', help='Set subscription to expire in 2 minutes (for email reminder test)')
        parser.add_argument('--restore-normal', action='store_true', help='Restore normal 1-year subscription')
        
    def handle(self, *args, **options):
        email = '5doubow@spamok.com'
        expire_in_5min = options['expire_in_5min']
        expire_in_2min = options['expire_in_2min']
        restore_normal = options['restore_normal']
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f"👤 Found user: {user.username} ({user.email})")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User with email {email} not found"))
            return
        
        # Get user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
            self.stdout.write(f"✅ Created new profile for {user.username}")
        
        now = timezone.now()
        
        if expire_in_5min:
            # Set subscription to expire in 5 minutes for testing
            new_expiry = now + timedelta(minutes=5)
            profile.paid_access_expiry_date = new_expiry
            profile.has_paid_access = True  # Keep active until expiry
            profile.payment_amount = 5.00
            profile.save()
            
            self.stdout.write(f"⏰ Set subscription to expire in 5 minutes for {user.username}")
            self.stdout.write(f"🕐 Current time: {now}")
            self.stdout.write(f"📅 Subscription will expire at: {new_expiry}")
            
        elif expire_in_2min:
            # Set subscription to expire in 2 minutes (for email reminder testing)
            new_expiry = now + timedelta(minutes=2)
            profile.paid_access_expiry_date = new_expiry
            profile.has_paid_access = True  # Keep active until expiry
            profile.payment_amount = 5.00
            profile.save()
            
            self.stdout.write(f"📧 Set subscription to expire in 2 minutes for {user.username}")
            self.stdout.write(f"🕐 Current time: {now}")
            self.stdout.write(f"📅 Subscription will expire at: {new_expiry}")
            
        elif restore_normal:
            # Restore normal 1-year subscription
            new_expiry = now + timedelta(days=365)
            profile.paid_access_expiry_date = new_expiry
            profile.has_paid_access = True
            profile.payment_amount = 5.00
            profile.save()
            
            self.stdout.write(f"🔄 Restored normal 1-year subscription for {user.username}")
            self.stdout.write(f"📅 Subscription will now expire at: {new_expiry}")
            
        # Show current status
        profile.refresh_from_db()
        time_until_expiry = profile.paid_access_expiry_date - now
        minutes_until_expiry = time_until_expiry.total_seconds() / 60
        
        self.stdout.write(f"📊 Current subscription status:")
        self.stdout.write(f"   💳 Has paid access: {profile.has_paid_access}")
        self.stdout.write(f"   💰 Payment amount: £{profile.payment_amount}")
        self.stdout.write(f"   📅 Expires: {profile.paid_access_expiry_date}")
        self.stdout.write(f"   ⏱️  Minutes until expiry: {minutes_until_expiry:.1f}")
        self.stdout.write(f"   ✅ Is currently active: {profile.is_paid_access_active}")
        
        if minutes_until_expiry <= 0:
            self.stdout.write(f"🔒 Subscription is EXPIRED")
        elif minutes_until_expiry <= 5:
            self.stdout.write(f"⚠️  Subscription expires in {minutes_until_expiry:.1f} minutes - test email reminders!")
        else:
            self.stdout.write(f"✅ Subscription is active")
        
        self.stdout.write(self.style.SUCCESS("✅ Subscription expiry testing setup completed!"))