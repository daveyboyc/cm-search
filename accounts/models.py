from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver

# Create your models here.


class UserProfile(models.Model):
    """Extends the default User model to include application-specific fields."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    has_paid_access = models.BooleanField(default=False, help_text="Indicates if the user has active paid access.")
    paid_access_expiry_date = models.DateTimeField(null=True, blank=True, help_text="The date and time when paid access expires.")
    payment_amount = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Amount paid for access (£2 = lists only, £5 = full access)")

    # Monthly trial tracking (1 week per 30-day cycle)
    trial_week_start = models.DateTimeField(null=True, blank=True, help_text="When the current 30-day trial cycle started.")
    trial_first_use = models.DateTimeField(null=True, blank=True, help_text="When user first accessed the site in current trial month.")
    trial_hours_used = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Hours used in current trial cycle.")
    
    # Legacy fields (to be removed in future migration)
    free_access_start_time = models.DateTimeField(null=True, blank=True, help_text="LEGACY: When the user's free access period started.")
    reminder_email_sent = models.BooleanField(default=False, help_text="LEGACY: Whether a reminder email has been sent for expired free access.")
    reminder_email_sent_at = models.DateTimeField(null=True, blank=True, help_text="LEGACY: When the reminder email was sent.")

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def is_paid_access_active(self):
        """Checks if the user currently has active paid access (£5/year)."""
        if not self.has_paid_access:
            return False
        if self.paid_access_expiry_date is None:
            # If expiry is null but has_paid_access is True, assume perpetual access
            return True
        return timezone.now() < self.paid_access_expiry_date
    
    def get_weekly_trial_hours_remaining(self):
        """
        Returns remaining trial hours for current cycle.
        Returns 168 hours (1 week) if new cycle or first use, 0.0 if expired.
        Special case: 5doubow@spamok.com gets 5-minute trial for testing.
        """
        now = timezone.now()
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        
        # SPECIAL TESTING CASE: 5doubow@spamok.com gets 5-minute trial
        if self.user.email == '5doubow@spamok.com':
            if not self.trial_first_use:
                # Start 5-minute trial
                logger.info(f"Testing trial available for {self.user.username}: 5 minutes remaining")
                return 5.0 / 60  # 5 minutes converted to hours (0.083 hours)
            
            # Calculate minutes used since first use
            elapsed_seconds = (now - self.trial_first_use).total_seconds()
            elapsed_minutes = elapsed_seconds / 60
            remaining_minutes = max(0.0, 5.0 - elapsed_minutes)  # 5-minute trial
            remaining_hours = remaining_minutes / 60  # Convert to hours
            
            logger.info(f"Testing trial check for {self.user.username}: {remaining_minutes:.1f} minutes ({remaining_hours:.3f} hours) remaining (elapsed: {elapsed_minutes:.1f} minutes)")
            return remaining_hours
        
        # NORMAL USERS: Standard 1-week monthly trial
        # Check if we need to start a new cycle (1 month = 30 days)
        reset_seconds = 2592000  # 30 days * 24 hours * 3600 seconds
        if not self.trial_week_start or (now - self.trial_week_start).total_seconds() >= reset_seconds:
            # Reset for new month
            self.trial_week_start = now
            self.trial_first_use = None
            self.trial_hours_used = 0.0
            self.save()
            logger.info(f"Trial reset for user {self.user.username}: new cycle started")
            return 168.0  # 1 week (7 days * 24 hours)
        
        # If they haven't used trial this cycle yet, they have full trial time
        if not self.trial_first_use:
            logger.info(f"Trial available for user {self.user.username}: {168.0} hours remaining")
            return 168.0  # 1 week (7 days * 24 hours)
        
        # Calculate hours used since first use this week
        elapsed_seconds = (now - self.trial_first_use).total_seconds()
        elapsed_hours = elapsed_seconds / 3600
        
        remaining = max(0.0, 168.0 - elapsed_hours)  # 1 week (7 days * 24 hours)
        logger.info(f"Trial check for user {self.user.username}: {remaining} hours remaining (elapsed: {elapsed_hours})")
        return remaining
    
    def start_trial_usage(self):
        """Start the trial usage timer if not already started this week."""
        if not self.trial_first_use:
            self.trial_first_use = timezone.now()
            self.save()
    
    @property
    def is_trial_expired(self):
        """Check if current week's trial is completely used up."""
        return self.get_weekly_trial_hours_remaining() <= 0
        
    # LEGACY METHODS (for backward compatibility during transition)
    @property
    def is_free_access_expired(self):
        """LEGACY: Use is_trial_expired instead."""
        return self.is_trial_expired
        
    @property 
    def free_access_time_remaining(self):
        """LEGACY: Returns remaining trial time in seconds."""
        hours_remaining = self.get_weekly_trial_hours_remaining()
        return int(hours_remaining * 3600)  # Convert to seconds


class RegistrationEmailRecord(models.Model):
    """Keeps a record of all registration emails sent, even if user accounts weren't created."""
    email = models.EmailField()
    timestamp = models.DateTimeField(auto_now_add=True)
    activation_link = models.TextField(blank=True, null=True)
    user_created = models.BooleanField(default=False)
    user_activated = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Registration Email Record"
        verbose_name_plural = "Registration Email Records"
    
    def __str__(self):
        status = "activated" if self.user_activated else ("created" if self.user_created else "pending")
        return f"{self.email} ({status}) - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


@receiver(post_delete, sender=User)
def cleanup_registration_records(sender, instance, **kwargs):
    """Clean up RegistrationEmailRecord entries when a user is deleted"""
    try:
        # Delete all registration records for this user's email
        RegistrationEmailRecord.objects.filter(email=instance.email).delete()
        print(f"Cleaned up registration records for deleted user: {instance.email}")
    except Exception as e:
        print(f"Error cleaning up registration records for {instance.email}: {e}")
