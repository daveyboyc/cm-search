#!/usr/bin/env python
"""
Script to check for orphaned user records and investigate registration issues.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, RegistrationEmailRecord

def check_user_records():
    """Check for user records related to davidcrawford83@gmail.com"""
    
    email = "davidcrawford83@gmail.com"
    print(f"=== Checking records for {email} ===\n")
    
    # Check User model
    try:
        user = User.objects.get(username=email)
        print(f"✓ User found: {user.username}")
        print(f"  - ID: {user.id}")
        print(f"  - Email: {user.email}")
        print(f"  - Is Active: {user.is_active}")
        print(f"  - Date Joined: {user.date_joined}")
        print(f"  - Last Login: {user.last_login}")
        
        # Check for UserProfile
        try:
            profile = user.profile
            print(f"✓ UserProfile found:")
            print(f"  - Has Paid Access: {profile.has_paid_access}")
            print(f"  - Paid Access Expiry: {profile.paid_access_expiry_date}")
            print(f"  - Payment Amount: {profile.payment_amount}")
        except UserProfile.DoesNotExist:
            print("✗ No UserProfile found for this user")
            
    except User.DoesNotExist:
        print(f"✗ No User found with username/email: {email}")
    
    # Check alternative: email field
    users_with_email = User.objects.filter(email=email)
    if users_with_email.exists():
        print(f"\n✓ Found {users_with_email.count()} user(s) with email field = {email}:")
        for user in users_with_email:
            print(f"  - Username: {user.username}, Active: {user.is_active}")
    else:
        print(f"\n✗ No users found with email field = {email}")
    
    # Check RegistrationEmailRecord
    email_records = RegistrationEmailRecord.objects.filter(email=email)
    if email_records.exists():
        print(f"\n✓ Found {email_records.count()} registration email record(s):")
        for record in email_records:
            print(f"  - Timestamp: {record.timestamp}")
            print(f"  - User Created: {record.user_created}")
            print(f"  - User Activated: {record.user_activated}")
            print(f"  - Error Message: {record.error_message}")
            print("  ---")
    else:
        print(f"\n✗ No registration email records found for {email}")
    
    # Check for any users with similar usernames/emails
    print(f"\n=== Similar records check ===")
    similar_users = User.objects.filter(username__icontains="davidcrawford")
    if similar_users.exists():
        print(f"Found {similar_users.count()} user(s) with 'davidcrawford' in username:")
        for user in similar_users:
            print(f"  - {user.username} (Active: {user.is_active})")
    
    similar_emails = User.objects.filter(email__icontains="davidcrawford")
    if similar_emails.exists():
        print(f"Found {similar_emails.count()} user(s) with 'davidcrawford' in email:")
        for user in similar_emails:
            print(f"  - {user.email} -> {user.username} (Active: {user.is_active})")

def check_all_inactive_users():
    """Check all inactive users to see if any should be cleaned up"""
    print(f"\n=== All inactive users ===")
    inactive_users = User.objects.filter(is_active=False)
    print(f"Found {inactive_users.count()} inactive user(s):")
    for user in inactive_users:
        print(f"  - {user.username} ({user.email}) - Joined: {user.date_joined}")

if __name__ == "__main__":
    check_user_records()
    check_all_inactive_users()