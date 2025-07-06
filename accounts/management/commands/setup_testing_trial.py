"""
Management command to set up a special 5-minute testing trial for 5doubow@spamok.com
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Set up 5-minute testing trial for 5doubow@spamok.com'
    
    def add_arguments(self, parser):
        parser.add_argument('--start-fresh', action='store_true', help='Start a fresh 5-minute trial')
        parser.add_argument('--expire-in-2min', action='store_true', help='Set trial to expire in 2 minutes (for email reminder test)')
        
    def handle(self, *args, **options):
        email = '5doubow@spamok.com'
        start_fresh = options['start_fresh']
        expire_in_2min = options['expire_in_2min']
        
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
        
        now = timezone.now()
        
        if start_fresh:
            # Start a fresh 5-minute trial
            # Set trial_first_use to now, so they get 5 minutes from now
            profile.trial_first_use = now
            profile.trial_week_start = now - timedelta(days=25)  # Prevent monthly reset
            profile.save()
            
            self.stdout.write(f"🆕 Started fresh 5-minute trial for {user.username}")
            self.stdout.write(f"🕐 Trial started at: {now}")
            self.stdout.write(f"⏰ Trial will expire at: {now + timedelta(minutes=5)}")
            
        elif expire_in_2min:
            # Set trial to expire in 2 minutes (for email reminder testing)
            # This means they've already used 3 minutes of their 5-minute trial
            three_minutes_ago = now - timedelta(minutes=3)
            profile.trial_first_use = three_minutes_ago
            profile.trial_week_start = now - timedelta(days=25)  # Prevent monthly reset
            profile.save()
            
            self.stdout.write(f"📧 Set trial to expire in 2 minutes for {user.username}")
            self.stdout.write(f"🕐 Trial 'started' at: {three_minutes_ago}")
            self.stdout.write(f"⏰ Trial will expire at: {now + timedelta(minutes=2)}")
            
        # Show current status
        # We need to simulate the trial calculation logic here
        if profile.trial_first_use:
            elapsed_seconds = (now - profile.trial_first_use).total_seconds()
            elapsed_minutes = elapsed_seconds / 60
            remaining_minutes = max(0, 5 - elapsed_minutes)  # 5-minute trial
            
            self.stdout.write(f"📊 Current status:")
            self.stdout.write(f"   ⏱️  Elapsed: {elapsed_minutes:.1f} minutes")
            self.stdout.write(f"   ⏳ Remaining: {remaining_minutes:.1f} minutes")
            
            if remaining_minutes <= 0:
                self.stdout.write(f"🔒 Trial is EXPIRED")
            elif remaining_minutes <= 2:
                self.stdout.write(f"⚠️  Trial expires in {remaining_minutes:.1f} minutes - reminder should be sent!")
            else:
                self.stdout.write(f"✅ Trial is active")
        
        self.stdout.write(self.style.SUCCESS("✅ Testing trial setup completed!"))
        self.stdout.write("Now the UserProfile.get_weekly_trial_hours_remaining() method needs to be updated to handle this special case.")