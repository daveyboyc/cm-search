"""
Subscription Management System
Handles subscription duration, renewal, and testing modes
"""
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """
    Centralized subscription management for easy testing/production switching
    """
    
    # Testing configuration
    TESTING_SUBSCRIPTION_DURATION = timedelta(minutes=5)
    TESTING_REMINDER_TIMES = [
        timedelta(minutes=2),  # Send reminder 2 minutes before expiry
    ]
    
    # Production configuration  
    PRODUCTION_SUBSCRIPTION_DURATION = timedelta(days=365)  # 1 year
    PRODUCTION_REMINDER_TIMES = [
        timedelta(days=30),   # Send reminder 1 month before expiry
        timedelta(days=7),    # Send reminder 1 week before expiry
    ]
    
    # Test users who get short subscriptions
    TEST_USERS = [
        '5doubow@spamok.com',
    ]
    
    @classmethod
    def is_test_user(cls, email):
        """Check if user should get test subscription duration"""
        return email.lower() in [user.lower() for user in cls.TEST_USERS]
    
    @classmethod
    def get_subscription_duration(cls, user_email):
        """Get subscription duration based on user and settings"""
        if cls.is_test_user(user_email):
            logger.info(f"TEST USER: {user_email} gets {cls.TESTING_SUBSCRIPTION_DURATION}")
            return cls.TESTING_SUBSCRIPTION_DURATION
        else:
            logger.info(f"PRODUCTION USER: {user_email} gets {cls.PRODUCTION_SUBSCRIPTION_DURATION}")
            return cls.PRODUCTION_SUBSCRIPTION_DURATION
    
    @classmethod
    def get_reminder_times(cls, user_email):
        """Get reminder times based on user and settings"""
        if cls.is_test_user(user_email):
            return cls.TESTING_REMINDER_TIMES
        else:
            return cls.PRODUCTION_REMINDER_TIMES
    
    @classmethod
    def create_subscription(cls, user_profile, payment_amount=5.00):
        """Create a new subscription with appropriate duration"""
        user_email = user_profile.user.email
        duration = cls.get_subscription_duration(user_email)
        
        # Set subscription details
        user_profile.has_paid_access = True
        user_profile.payment_amount = payment_amount
        user_profile.paid_access_expiry_date = timezone.now() + duration
        user_profile.save()
        
        expiry_str = user_profile.paid_access_expiry_date.strftime('%Y-%m-%d %H:%M:%S %Z')
        logger.info(f"SUBSCRIPTION CREATED: {user_email} expires at {expiry_str}")
        
        return user_profile
    
    @classmethod
    def should_send_reminder(cls, user_profile):
        """Check if user should receive expiry reminder email"""
        if not user_profile.has_paid_access or not user_profile.paid_access_expiry_date:
            return False
        
        # Already expired - no reminder needed
        if not user_profile.is_paid_access_active:
            return False
        
        user_email = user_profile.user.email
        reminder_times = cls.get_reminder_times(user_email)
        time_until_expiry = user_profile.paid_access_expiry_date - timezone.now()
        
        # Check if time until expiry matches any reminder time (within 1 minute tolerance)
        for reminder_time in reminder_times:
            tolerance = timedelta(minutes=1)
            if abs(time_until_expiry - reminder_time) <= tolerance:
                logger.info(f"REMINDER DUE: {user_email} expires in {time_until_expiry}")
                return True
        
        return False
    
    @classmethod
    def get_subscription_type_display(cls, user_email):
        """Get display name for subscription type"""
        if cls.is_test_user(user_email):
            duration = cls.TESTING_SUBSCRIPTION_DURATION
            if duration.total_seconds() < 3600:  # Less than 1 hour
                minutes = int(duration.total_seconds() / 60)
                return f"{minutes}-minute testing subscription"
            else:
                hours = int(duration.total_seconds() / 3600)
                return f"{hours}-hour testing subscription"
        else:
            return "£5/year subscription"
    
    @classmethod
    def enable_production_mode(cls):
        """Switch all users to production subscription durations"""
        logger.warning("PRODUCTION MODE: All new subscriptions will be 1 year")
        # Could modify TEST_USERS list or add a global setting
        cls.TEST_USERS = []
    
    @classmethod
    def enable_testing_mode(cls, test_emails=None):
        """Add users to testing mode"""
        if test_emails:
            cls.TEST_USERS.extend(test_emails)
            logger.info(f"TESTING MODE: Added test users: {test_emails}")
    
    @classmethod
    def get_status_summary(cls):
        """Get summary of current subscription settings"""
        return {
            'test_users': cls.TEST_USERS,
            'testing_duration': str(cls.TESTING_SUBSCRIPTION_DURATION),
            'production_duration': str(cls.PRODUCTION_SUBSCRIPTION_DURATION),
            'testing_reminders': [str(t) for t in cls.TESTING_REMINDER_TIMES],
            'production_reminders': [str(t) for t in cls.PRODUCTION_REMINDER_TIMES],
        }