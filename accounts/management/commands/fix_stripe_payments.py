"""
Management command to help fix Stripe payment issues and manually activate users.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone
from datetime import timedelta
from django.db import models
import stripe
from django.conf import settings


class Command(BaseCommand):
    help = 'Fix Stripe payment issues and manually process pending payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-user',
            type=str,
            help='Check payment status for a specific user email',
        )
        
        parser.add_argument(
            '--activate-user',
            type=str,
            help='Manually activate paid access for a user email',
        )
        
        parser.add_argument(
            '--list-pending',
            action='store_true',
            help='List users with potential pending payments',
        )
        
        parser.add_argument(
            '--test-webhook',
            action='store_true',
            help='Show webhook configuration info',
        )

    def handle(self, *args, **options):
        
        if options['check_user']:
            self.check_user_payment(options['check_user'])
            
        elif options['activate_user']:
            self.activate_user_payment(options['activate_user'])
            
        elif options['list_pending']:
            self.list_pending_payments()
            
        elif options['test_webhook']:
            self.test_webhook_config()
            
        else:
            self.show_help()

    def check_user_payment(self, email):
        """Check a specific user's payment status."""
        try:
            user = User.objects.get(email=email)
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            self.stdout.write(f"\n👤 User: {user.email}")
            self.stdout.write(f"   📅 Joined: {user.date_joined}")
            self.stdout.write(f"   ✅ Active: {user.is_active}")
            self.stdout.write(f"   💳 Has paid access: {profile.has_paid_access}")
            self.stdout.write(f"   🔓 Paid access active: {profile.is_paid_access_active}")
            
            if profile.paid_access_expiry_date:
                self.stdout.write(f"   ⏰ Expires: {profile.paid_access_expiry_date}")
            
            self.stdout.write(f"   ⏱️  Trial hours remaining: {profile.get_weekly_trial_hours_remaining()}")
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {email} not found')
            )

    def activate_user_payment(self, email):
        """Manually activate paid access for a user."""
        try:
            user = User.objects.get(email=email)
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Set paid access for 1 year
            profile.has_paid_access = True
            profile.paid_access_expiry_date = timezone.now() + timedelta(days=365)
            profile.payment_amount = 5.00  # £5/year
            profile.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Activated paid access for {email}')
            )
            self.stdout.write(f"   💳 Expires: {profile.paid_access_expiry_date}")
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {email} not found')
            )

    def list_pending_payments(self):
        """List users who might have pending payments."""
        self.stdout.write("\n🔍 Looking for users with potential payment issues...")
        
        # Find users who:
        # 1. Are active
        # 2. Don't have paid access
        # 3. Joined recently (last 7 days)
        # 4. Either used trial time OR joined very recently (indicating payment attempt)
        
        recent_cutoff = timezone.now() - timedelta(days=7)
        very_recent_cutoff = timezone.now() - timedelta(hours=24)  # Last 24 hours
        
        profiles = UserProfile.objects.filter(
            user__is_active=True,
            has_paid_access=False,
            user__date_joined__gte=recent_cutoff
        ).filter(
            # Either used some trial time OR joined very recently (payment attempt)
            models.Q(trial_hours_used__gt=0.1) | 
            models.Q(user__date_joined__gte=very_recent_cutoff)
        ).select_related('user')
        
        if not profiles:
            self.stdout.write("✅ No users with potential payment issues found")
            return
        
        self.stdout.write(f"\n📋 Found {profiles.count()} users with potential payment issues:")
        
        for profile in profiles:
            user = profile.user
            hours_used = float(profile.trial_hours_used)
            hours_remaining = profile.get_weekly_trial_hours_remaining()
            
            self.stdout.write(f"\n👤 {user.email}")
            self.stdout.write(f"   📅 Joined: {user.date_joined.strftime('%Y-%m-%d %H:%M')}")
            self.stdout.write(f"   ⏱️  Trial used: {hours_used:.1f}h, remaining: {hours_remaining:.1f}h")
            self.stdout.write(f"   💳 Payment status: No paid access")

    def test_webhook_config(self):
        """Show webhook configuration information."""
        self.stdout.write("\n🔗 Webhook Configuration:")
        self.stdout.write("=" * 50)
        
        # Check webhook secret
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        if webhook_secret:
            self.stdout.write(f"✅ Webhook secret: Configured (ends with ...{webhook_secret[-4:]})")
        else:
            self.stdout.write("❌ Webhook secret: NOT CONFIGURED")
        
        # Check Stripe keys
        stripe_secret = getattr(settings, 'STRIPE_SECRET_KEY', None)
        if stripe_secret:
            self.stdout.write(f"✅ Stripe secret key: Configured (starts with {stripe_secret[:7]}...)")
        else:
            self.stdout.write("❌ Stripe secret key: NOT CONFIGURED")
        
        # Show URLs
        self.stdout.write("\n📍 Webhook URLs:")
        self.stdout.write("   Django URLs available:")
        self.stdout.write("   - /accounts/stripe/webhook/ (original)")
        self.stdout.write("   - /account/stripe-webhook/ (Stripe configured)")
        
        self.stdout.write("\n💡 Stripe Configuration:")
        self.stdout.write("   Current Stripe webhook URL: https://neso-cmr-search-da0169863eae.herokuapp.com/account/stripe-webhook/")
        self.stdout.write("   Events to listen for: checkout.session.completed")
        
        self.stdout.write("\n🔧 To fix webhook issues:")
        self.stdout.write("   1. Deploy this code to Heroku")
        self.stdout.write("   2. Set STRIPE_WEBHOOK_SECRET environment variable")
        self.stdout.write("   3. Test webhook with: curl -X POST https://your-site.com/account/stripe-webhook/")

    def show_help(self):
        """Show usage help."""
        self.stdout.write("\n🛠️  Stripe Payment Fix Tool")
        self.stdout.write("=" * 40)
        self.stdout.write("\nUsage:")
        self.stdout.write("  python manage.py fix_stripe_payments --check-user user@email.com")
        self.stdout.write("  python manage.py fix_stripe_payments --activate-user user@email.com")
        self.stdout.write("  python manage.py fix_stripe_payments --list-pending")
        self.stdout.write("  python manage.py fix_stripe_payments --test-webhook")
        
        self.stdout.write("\n📝 Common scenarios:")
        self.stdout.write("  1. User paid but access not activated:")
        self.stdout.write("     → Use --activate-user email@domain.com")
        self.stdout.write("  2. Check if webhook is working:")
        self.stdout.write("     → Use --test-webhook")
        self.stdout.write("  3. Find users with payment issues:")
        self.stdout.write("     → Use --list-pending")