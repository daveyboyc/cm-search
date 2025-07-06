#!/usr/bin/env python
"""
Script to properly delete a user and all related records.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, RegistrationEmailRecord
from django.db import transaction

def delete_user_completely(email):
    """Delete user and all related records completely"""
    
    print(f"=== Attempting to delete user: {email} ===\n")
    
    with transaction.atomic():
        deleted_items = []
        
        # 1. Delete User (this will cascade to UserProfile due to CASCADE relationship)
        try:
            user = User.objects.get(username=email)
            user_id = user.id
            print(f"✓ Found user: {user.username} (ID: {user_id})")
            
            # Check for UserProfile before deletion
            try:
                profile = user.profile
                print(f"✓ Found UserProfile: {profile}")
            except UserProfile.DoesNotExist:
                print("- No UserProfile found")
            
            # Delete the user (this will cascade delete the UserProfile)
            user.delete()
            deleted_items.append(f"User: {email} (ID: {user_id})")
            print(f"✓ Deleted user and cascaded UserProfile")
            
        except User.DoesNotExist:
            print(f"✗ No user found with username: {email}")
            return False
        
        # 2. Clean up RegistrationEmailRecord entries
        email_records = RegistrationEmailRecord.objects.filter(email=email)
        if email_records.exists():
            count = email_records.count()
            email_records.delete()
            deleted_items.append(f"RegistrationEmailRecord entries: {count}")
            print(f"✓ Deleted {count} registration email record(s)")
        else:
            print("- No registration email records found")
        
        print(f"\n=== Deletion Summary ===")
        for item in deleted_items:
            print(f"  - {item}")
        
        print(f"\n✅ User {email} and all related records have been completely deleted!")
        return True

def verify_deletion(email):
    """Verify the user has been completely deleted"""
    print(f"\n=== Verifying deletion of {email} ===")
    
    # Check User
    user_exists = User.objects.filter(username=email).exists()
    email_exists = User.objects.filter(email=email).exists()
    
    if user_exists or email_exists:
        print(f"✗ User still exists!")
        if user_exists:
            user = User.objects.get(username=email)
            print(f"  - Username match: {user.username}, Active: {user.is_active}")
        if email_exists:
            user = User.objects.get(email=email)
            print(f"  - Email match: {user.email}, Active: {user.is_active}")
        return False
    else:
        print(f"✓ No User records found")
    
    # Check RegistrationEmailRecord
    email_records = RegistrationEmailRecord.objects.filter(email=email)
    if email_records.exists():
        print(f"✗ {email_records.count()} registration email record(s) still exist")
        return False
    else:
        print(f"✓ No registration email records found")
    
    print(f"✅ Verification complete - {email} has been completely removed!")
    return True

if __name__ == "__main__":
    email = "davidcrawford83@gmail.com"
    
    # First show current state
    print("=== Current State ===")
    try:
        user = User.objects.get(username=email)
        print(f"User exists: {user.username}, Active: {user.is_active}")
    except User.DoesNotExist:
        print("User does not exist")
    
    # Ask for confirmation
    confirm = input(f"\nAre you sure you want to DELETE {email} and ALL related records? (type 'DELETE' to confirm): ")
    
    if confirm == 'DELETE':
        success = delete_user_completely(email)
        if success:
            verify_deletion(email)
    else:
        print("Deletion cancelled.")