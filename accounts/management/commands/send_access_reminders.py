from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.utils import check_and_send_expired_reminders, send_access_expired_reminder
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check for users with expired free access and send reminder emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually sending emails',
        )
        parser.add_argument(
            '--force-user',
            type=str,
            help='Force send reminder to specific user by email (bypasses normal checks)',
        )
        parser.add_argument(
            '--list-expired',
            action='store_true',
            help='List all users with expired free access',
        )
        parser.add_argument(
            '--reset-reminders',
            action='store_true',
            help='Reset reminder email flags for testing (use with caution)',
        )

    def handle(self, *args, **options):
        
        # Reset reminder flags for testing
        if options['reset_reminders']:
            reset_count = UserProfile.objects.filter(reminder_email_sent=True).update(
                reminder_email_sent=False,
                reminder_email_sent_at=None
            )
            self.stdout.write(
                self.style.WARNING(f'Reset reminder flags for {reset_count} users')
            )
            return
        
        # List expired users
        if options['list_expired']:
            expired_profiles = UserProfile.objects.filter(
                has_paid_access=False,
                free_access_start_time__isnull=False,
                free_access_start_time__lt=timezone.now() - timedelta(hours=24)
            ).select_related('user').order_by('free_access_start_time')
            
            if not expired_profiles:
                self.stdout.write(self.style.SUCCESS('No users with expired free access found.'))
                return
                
            self.stdout.write(self.style.NOTICE(f'Found {expired_profiles.count()} users with expired free access:'))
            for profile in expired_profiles:
                days_expired = (timezone.now() - (profile.free_access_start_time + timedelta(hours=24))).days
                reminder_status = "✅ Sent" if profile.reminder_email_sent else "❌ Not sent"
                sent_time = ""
                if profile.reminder_email_sent_at:
                    sent_time = f" ({profile.reminder_email_sent_at.strftime('%Y-%m-%d %H:%M')})"
                
                self.stdout.write(
                    f"  {profile.user.email} - "
                    f"Expired {days_expired} days ago - "
                    f"Reminder: {reminder_status}{sent_time}"
                )
            return
        
        # Force send to specific user
        if options['force_user']:
            email = options['force_user']
            try:
                user = User.objects.get(email=email)
                if options['dry_run']:
                    self.stdout.write(f"DRY RUN: Would send reminder email to {email}")
                else:
                    success = send_access_expired_reminder(user)
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(f'Successfully sent reminder email to {email}')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Failed to send reminder email to {email}')
                        )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with email {email} not found')
                )
            return
        
        # Normal operation - check and send reminders
        if options['dry_run']:
            # Show what would be done
            expired_profiles = UserProfile.objects.filter(
                has_paid_access=False,
                reminder_email_sent=False,
                free_access_start_time__isnull=False,
                free_access_start_time__lt=timezone.now() - timedelta(hours=24)
            ).select_related('user')
            
            self.stdout.write(
                self.style.NOTICE(f'DRY RUN: Would send reminder emails to {expired_profiles.count()} users:')
            )
            for profile in expired_profiles:
                self.stdout.write(f"  - {profile.user.email}")
        else:
            # Actually send emails
            emails_sent = check_and_send_expired_reminders()
            if emails_sent > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully sent {emails_sent} reminder emails')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No reminder emails needed to be sent')
                ) 