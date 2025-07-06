#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone

# Check and reset testuser
try:
    user1 = User.objects.get(username='testuser')
    profile1 = user1.profile
    print(f"\ntestuser status:")
    print(f"  - Has paid access: {profile1.has_paid_access}")
    print(f"  - Free access start: {profile1.free_access_start_time}")
    print(f"  - Is expired: {profile1.is_free_access_expired}")
    
    # Reset trial
    profile1.free_access_start_time = timezone.now()
    profile1.reminder_email_sent = False
    profile1.reminder_email_sent_at = None
    profile1.save()
    print(f"  ✅ Reset trial period to start now")
except User.DoesNotExist:
    print("testuser not found")

# Check and reset testuser2
try:
    user2 = User.objects.get(username='testuser2')
    profile2 = user2.profile
    print(f"\ntestuser2 status:")
    print(f"  - Has paid access: {profile2.has_paid_access}")
    print(f"  - Free access start: {profile2.free_access_start_time}")
    print(f"  - Is expired: {profile2.is_free_access_expired}")
    
    # Reset trial
    profile2.free_access_start_time = timezone.now()
    profile2.reminder_email_sent = False
    profile2.reminder_email_sent_at = None
    profile2.save()
    print(f"  ✅ Reset trial period to start now")
except User.DoesNotExist:
    print("testuser2 not found")

print("\nBoth users should now have fresh 24-hour trials!")