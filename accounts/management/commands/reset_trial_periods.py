"""
Management command to reset trial periods for users who haven't paid.
Run this monthly to give users another 24-hour trial period.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset trial periods for users who have not paid (run monthly)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would happen without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Find users eligible for trial reset
        # Criteria: 
        # 1. Not paid (has_paid_access = False)
        # 2. Trial expired (free_access_start_time > 30 days ago)
        # 3. Account created > 30 days ago
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        eligible_users = UserProfile.objects.filter(
            has_paid_access=False,
            free_access_start_time__lt=thirty_days_ago,
            user__date_joined__lt=thirty_days_ago
        )
        
        self.stdout.write(f"\n📊 Found {eligible_users.count()} users eligible for trial reset")
        
        reset_count = 0
        for profile in eligible_users:
            user = profile.user
            old_start_time = profile.free_access_start_time
            
            if not dry_run:
                # Reset the trial period
                profile.free_access_start_time = timezone.now()
                profile.reminder_email_sent = False
                profile.reminder_email_sent_at = None
                profile.save()
            
            reset_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {'Would reset' if dry_run else 'Reset'} trial for {user.email} "
                    f"(last trial: {old_start_time.strftime('%Y-%m-%d') if old_start_time else 'Never'})"
                )
            )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 {'Would reset' if dry_run else 'Reset'} {reset_count} trial periods"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n💡 Run without --dry-run to actually reset trials"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✨ Trial periods reset successfully!"
                )
            )
            
        # Suggest cron job setup
        self.stdout.write(
            self.style.WARNING(
                "\n📅 To run this monthly, add to your crontab:\n"
                "0 0 1 * * python manage.py reset_trial_periods\n"
                "(Runs at midnight on the 1st of each month)"
            )
        )