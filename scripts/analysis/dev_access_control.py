#!/usr/bin/env python
"""
Quick test script to verify multi-tier access control
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
from checker.access_control import get_user_access_level, can_access_map_view, can_access_premium_features, get_access_message

class MockUser:
    def __init__(self, is_authenticated=False, has_paid_access=False, is_superuser=False, is_staff=False):
        self.is_authenticated = is_authenticated
        self.is_superuser = is_superuser
        self.is_staff = is_staff
        if is_authenticated and has_paid_access:
            self.profile = MockProfile(has_paid_access=True)
        elif is_authenticated:
            self.profile = MockProfile(has_paid_access=False)

class MockProfile:
    def __init__(self, has_paid_access=False):
        self.has_paid_access = has_paid_access

def test_access_control():
    print("Testing Multi-Tier Access Control")
    print("=" * 50)
    
    # Test 1: Unauthenticated user
    print("\n1. Testing Unauthenticated User:")
    unauth_user = MockUser(is_authenticated=False)
    print(f"   Access Level: {get_user_access_level(unauth_user)}")
    print(f"   Can Access Map: {can_access_map_view(unauth_user)}")
    print(f"   Can Access Premium: {can_access_premium_features(unauth_user)}")
    access_msg = get_access_message(unauth_user)
    if access_msg:
        print(f"   Message: {access_msg['title']} - {access_msg['message']}")
    
    # Test 2: Registered user (no payment)
    print("\n2. Testing Registered User (No Payment):")
    reg_user = MockUser(is_authenticated=True, has_paid_access=False)
    print(f"   Access Level: {get_user_access_level(reg_user)}")
    print(f"   Can Access Map: {can_access_map_view(reg_user)}")
    print(f"   Can Access Premium: {can_access_premium_features(reg_user)}")
    access_msg = get_access_message(reg_user)
    if access_msg:
        print(f"   Message: {access_msg['title']} - {access_msg['message']}")
    
    # Test 3: Premium user (paid access)
    print("\n3. Testing Premium User (Paid Access):")
    premium_user = MockUser(is_authenticated=True, has_paid_access=True)
    print(f"   Access Level: {get_user_access_level(premium_user)}")
    print(f"   Can Access Map: {can_access_map_view(premium_user)}")
    print(f"   Can Access Premium: {can_access_premium_features(premium_user)}")
    access_msg = get_access_message(premium_user)
    print(f"   Message: {access_msg if access_msg else 'No restrictions - full access'}")
    
    # Test 4: Admin/Superuser
    print("\n4. Testing Admin/Superuser:")
    admin_user = MockUser(is_authenticated=True, is_superuser=True)
    print(f"   Access Level: {get_user_access_level(admin_user)}")
    print(f"   Can Access Map: {can_access_map_view(admin_user)}")
    print(f"   Can Access Premium: {can_access_premium_features(admin_user)}")
    access_msg = get_access_message(admin_user)
    print(f"   Message: {access_msg if access_msg else 'No restrictions - full access'}")
    
    # Test 5: Staff user
    print("\n5. Testing Staff User:")
    staff_user = MockUser(is_authenticated=True, is_staff=True)
    print(f"   Access Level: {get_user_access_level(staff_user)}")
    print(f"   Can Access Map: {can_access_map_view(staff_user)}")
    print(f"   Can Access Premium: {can_access_premium_features(staff_user)}")
    access_msg = get_access_message(staff_user)
    print(f"   Message: {access_msg if access_msg else 'No restrictions - full access'}")
    
    print("\n" + "=" * 50)
    print("✅ Multi-tier access control test completed!")

if __name__ == "__main__":
    test_access_control()