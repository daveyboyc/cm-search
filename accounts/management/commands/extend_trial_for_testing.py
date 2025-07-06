"""
Management command to extend user trials for testing payment flows
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Extend user trial for testing payment flows'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email address of user to extend')
        parser.add_argument('--days', type=int, default=7, help='Number of days to extend trial (default: 7)')
        parser.add_argument('--reset-trial', action='store_true', help='Reset trial to full duration')
        parser.add_argument('--make-expired', action='store_true', help='Make trial expired for testing payment flow')
    
    def handle(self, *args, **options):
        email = options['email']
        days = options['days']
        reset_trial = options['reset_trial']
        make_expired = options['make_expired']
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f"👤 Found user: {user.username} ({user.email})")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User with email {email} not found"))
            return
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
            self.stdout.write(f"✅ Created new profile for {user.username}")
        
        # Show current trial status
        current_hours = profile.get_weekly_trial_hours_remaining()
        self.stdout.write(f"📊 Current trial status: {current_hours:.2f} hours remaining")
        
        if make_expired:
            # Make trial expired by setting hours used to max
            profile.trial_hours_used = 168.0  # Full week used
            profile.save()
            self.stdout.write(f"⏰ Made trial expired for {user.username}")
            
            # Verify expiry
            remaining_hours = profile.get_weekly_trial_hours_remaining()
            self.stdout.write(f"✅ Trial now expired: {remaining_hours:.2f} hours remaining")
            
        elif reset_trial:
            # Reset trial to full duration
            profile.trial_hours_used = 0.0
            profile.trial_week_start = timezone.now()
            profile.save()
            self.stdout.write(f"🔄 Reset trial to full duration for {user.username}")
            
            # Verify reset
            remaining_hours = profile.get_weekly_trial_hours_remaining()
            self.stdout.write(f"✅ Trial reset: {remaining_hours:.2f} hours remaining")
            
        else:
            # Extend trial by moving start date back
            if profile.trial_week_start:
                # Move start date back by specified days
                new_start = profile.trial_week_start - timedelta(days=days)
                profile.trial_week_start = new_start
                profile.save()
                self.stdout.write(f"📅 Extended trial by {days} days for {user.username}")
                self.stdout.write(f"🕐 New trial start: {new_start}")
            else:
                # Set trial start to past date for extended access
                past_date = timezone.now() - timedelta(days=days)
                profile.trial_week_start = past_date
                profile.trial_hours_used = 0.0
                profile.save()
                self.stdout.write(f"📅 Set trial start {days} days ago for {user.username}")
            
            # Show new trial status
            new_hours = profile.get_weekly_trial_hours_remaining()
            self.stdout.write(f"✅ New trial status: {new_hours:.2f} hours remaining")
        
        # Show access level
        from checker.access_control import get_user_access_level
        access_level = get_user_access_level(user)
        self.stdout.write(f"🔑 User access level: {access_level}")
        
        # Show next reset date
        if profile.trial_week_start:
            next_reset = profile.trial_week_start + timedelta(days=30)
            self.stdout.write(f"📆 Next trial reset: {next_reset}")
        
        self.stdout.write(self.style.SUCCESS("✅ Trial modification completed successfully!"))