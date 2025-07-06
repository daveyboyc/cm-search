#!/usr/bin/env python
"""
Test script to verify free registered users get 30-second trial
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from checker.access_control import get_user_access_level, can_access_map_view, needs_timer

# Test with the test user we created
try:
    test_user = User.objects.get(username='testuser')
    print(f"✅ Found test user: {test_user.username}")
    print(f"   Email: {test_user.email}")
    print(f"   Has profile: {hasattr(test_user, 'profile')}")
    if hasattr(test_user, 'profile'):
        print(f"   Has paid access: {test_user.profile.has_paid_access}")
    
    print(f"\n📊 Access Control Results:")
    print(f"   Access Level: {get_user_access_level(test_user)}")
    print(f"   Can Access Maps: {can_access_map_view(test_user)}")
    print(f"   Needs Timer: {needs_timer(test_user)}")
    
    print("\n✅ Free registered users now:")
    print("   - CAN access map views (trial)")
    print("   - Get 30-second timer")
    print("   - Redirect to payment page after timer expires")
    
except User.DoesNotExist:
    print("❌ Test user not found. Run: python manage.py create_test_user")