"""
Management command to customize trial settings for specific users.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone


class Command(BaseCommand):
    help = 'Customize trial hours for specific users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            required=True,
            help='Email of the user to customize',
        )
        
        parser.add_argument(
            '--trial-hours',
            type=float,
            required=True,
            help='Number of trial hours to set (e.g., 48.0)',
        )
        
        parser.add_argument(
            '--reset-trial',
            action='store_true',
            help='Reset the user\'s trial cycle to start fresh',
        )

    def handle(self, *args, **options):
        email = options['user_email']
        trial_hours = options['trial_hours']
        reset_trial = options['reset_trial']
        
        try:
            user = User.objects.get(email=email)
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            self.stdout.write(f"\n👤 Customizing trial for: {email}")
            self.stdout.write(f"📊 Current status:")
            self.stdout.write(f"   Trial hours remaining: {profile.get_weekly_trial_hours_remaining():.1f}h")
            self.stdout.write(f"   Trial week start: {profile.trial_week_start}")
            self.stdout.write(f"   Trial first use: {profile.trial_first_use}")
            
            if reset_trial:
                # Reset trial cycle
                profile.trial_week_start = timezone.now()
                profile.trial_first_use = None
                profile.trial_hours_used = 0.0
                self.stdout.write(f"🔄 Trial cycle reset")
            
            # Calculate how to set the trial to give exactly the desired hours
            now = timezone.now()
            
            if not profile.trial_first_use:
                # User hasn't started trial yet - set first use to give exact hours
                hours_to_subtract = 168.0 - trial_hours  # Standard is 168h
                profile.trial_first_use = now - timezone.timedelta(hours=hours_to_subtract)
                self.stdout.write(f"⏰ Set trial first use to: {profile.trial_first_use}")
            else:
                # User has started trial - adjust the first use time
                elapsed_hours = (now - profile.trial_first_use).total_seconds() / 3600
                current_remaining = max(0.0, 168.0 - elapsed_hours)
                
                # Adjust first use time to give exactly the desired remaining hours
                target_elapsed = 168.0 - trial_hours
                profile.trial_first_use = now - timezone.timedelta(hours=target_elapsed)
                self.stdout.write(f"⏰ Adjusted trial first use to: {profile.trial_first_use}")
            
            profile.save()
            
            # Verify the change
            new_remaining = profile.get_weekly_trial_hours_remaining()
            self.stdout.write(f"\n✅ Trial customization complete!")
            self.stdout.write(f"📊 New status:")
            self.stdout.write(f"   Trial hours remaining: {new_remaining:.1f}h")
            self.stdout.write(f"   Target hours: {trial_hours:.1f}h")
            self.stdout.write(f"   Difference: {abs(new_remaining - trial_hours):.2f}h")
            
            if abs(new_remaining - trial_hours) < 0.1:
                self.stdout.write(self.style.SUCCESS(f"🎯 Successfully set trial to {trial_hours}h for {email}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Trial set to {new_remaining:.1f}h (close to target {trial_hours}h)"))
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {email} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error customizing trial: {e}')
            )