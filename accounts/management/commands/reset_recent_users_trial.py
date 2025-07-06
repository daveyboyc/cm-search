"""
Management command to reset trial periods for recent users who signed up
during the testing period when limits were only 2 minutes.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset trial periods for recent users who signed up during testing period and send notification emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would happen without making changes',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days back to consider recent users (default: 7)',
        )
        parser.add_argument(
            '--send-emails',
            action='store_true',
            help='Send notification emails to reset users',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_back = options['days']
        send_emails = options['send_emails']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Find recent users who signed up during the testing period
        cutoff_date = timezone.now() - timedelta(days=days_back)
        recent_users = User.objects.filter(
            date_joined__gte=cutoff_date,
            is_active=True
        ).select_related('profile').order_by('-date_joined')
        
        self.stdout.write(f"\n📊 Found {recent_users.count()} users who signed up in the last {days_back} days")
        
        reset_count = 0
        email_count = 0
        
        for user in recent_users:
            # Get or create profile
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                if not dry_run:
                    profile = UserProfile.objects.create(user=user)
                else:
                    profile = None
            
            # Skip if user has paid access
            if profile and profile.has_paid_access:
                self.stdout.write(f"⏭️  Skipping {user.email} (already has paid access)")
                continue
            
            old_trial_start = profile.trial_week_start if profile else None
            
            if not dry_run:
                # Reset their trial period completely
                profile.trial_week_start = timezone.now()
                profile.trial_first_use = None
                profile.trial_hours_used = 0.0
                profile.save()
                
                # Send email notification if requested
                if send_emails:
                    email_sent = self.send_reset_notification(user)
                    if email_sent:
                        email_count += 1
            
            reset_count += 1
            email_status = ""
            if send_emails:
                email_status = " + email sent" if not dry_run else " + would send email"
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {'Would reset' if dry_run else 'Reset'} trial for {user.email} "
                    f"(joined: {user.date_joined.strftime('%Y-%m-%d %H:%M')})"
                    f"{email_status}"
                )
            )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 {'Would reset' if dry_run else 'Reset'} {reset_count} trial periods"
            )
        )
        
        if send_emails:
            self.stdout.write(
                self.style.SUCCESS(
                    f"📧 {'Would send' if dry_run else 'Sent'} {email_count} notification emails"
                )
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n💡 Run without --dry-run to actually reset trials"
                    f"{' and send emails' if send_emails else ''}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✨ Trial periods reset successfully!"
                )
            )

    def send_reset_notification(self, user):
        """
        Send a notification email to user about their trial reset.
        Returns True if email was sent successfully, False otherwise.
        """
        try:
            # Generate URLs
            upgrade_url = reverse('accounts:initiate_payment')
            upgrade_link = f"{settings.SITE_SCHEME}://{settings.SITE_DOMAIN}{upgrade_url}"
            site_url = f"{settings.SITE_SCHEME}://{settings.SITE_DOMAIN}"
            
            # Render email content
            subject = 'Great News! Your Capacity Market Search Trial Has Been Upgraded'
            message = render_to_string('accounts/trial_reset_notification_email.html', {
                'user': user,
                'upgrade_link': upgrade_link,
                'site_url': site_url,
            })
            
            # Send email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
            
            logger.info(f"Successfully sent trial reset notification to: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send trial reset notification to {user.email}: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to send email to {user.email}: {str(e)}")
            )
            return False