from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def start_free_access_timer(user):
    """
    Start the free access timer for a user if not already started.
    """
    from .models import UserProfile
    
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Only start timer if not already started and user hasn't paid
    if not profile.free_access_start_time and not profile.has_paid_access:
        profile.free_access_start_time = timezone.now()
        profile.save()
        logger.info(f"Started free access timer for user: {user.username}")
        return True
    return False

def send_access_expired_reminder(user):
    """
    Send a reminder email to a user whose free access has expired.
    Returns True if email was sent successfully, False otherwise.
    """
    from .models import UserProfile
    
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        logger.error(f"No UserProfile found for user: {user.username}")
        return False
    
    # Don't send if already sent or user has paid access
    if profile.reminder_email_sent or profile.has_paid_access:
        return False
    
    # Don't send if free access hasn't actually expired
    if not profile.is_free_access_expired:
        return False
    
    try:
        # Generate upgrade link
        upgrade_url = reverse('accounts:initiate_payment')
        upgrade_link = f"{settings.SITE_SCHEME}://{settings.SITE_DOMAIN}{upgrade_url}"
        
        # Render email content
        subject = 'Your Free Access to Capacity Market Search Has Expired'
        message = render_to_string('accounts/access_expired_reminder_email.html', {
            'user': user,
            'upgrade_link': upgrade_link,
        })
        
        # Send email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        # Mark as sent
        profile.reminder_email_sent = True
        profile.reminder_email_sent_at = timezone.now()
        profile.save()
        
        logger.info(f"Successfully sent access expired reminder to: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send access expired reminder to {user.email}: {str(e)}")
        return False

def check_and_send_expired_reminders():
    """
    Check all users with expired free access and send reminder emails if needed.
    Returns the number of emails sent.
    """
    from .models import UserProfile
    
    # Find users with expired free access who haven't received reminder emails
    expired_profiles = UserProfile.objects.filter(
        has_paid_access=False,
        reminder_email_sent=False,
        free_access_start_time__isnull=False,
        free_access_start_time__lt=timezone.now() - timedelta(hours=24)
    ).select_related('user')
    
    emails_sent = 0
    for profile in expired_profiles:
        if send_access_expired_reminder(profile.user):
            emails_sent += 1
    
    logger.info(f"Checked expired access reminders: {emails_sent} emails sent out of {expired_profiles.count()} expired users")
    return emails_sent

def get_or_create_user_profile(user):
    """
    Get or create a UserProfile for a user.
    """
    from .models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)
    return profile 