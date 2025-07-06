#!/usr/bin/env python3
"""
Debug testuser3 access level and profile
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from checker.access_control import get_user_access_level, can_access_map_view, can_access_list_view
from django.utils import timezone

def debug_testuser3():
    """Debug testuser3 setup"""
    try:
        # Check if user exists
        user = User.objects.get(username='testuser3')
        print(f"✅ testuser3 found: {user}")
        
        # Check profile
        if hasattr(user, 'profile') and user.profile:
            profile = user.profile
            print(f"✅ Profile found:")
            print(f"   has_paid_access: {profile.has_paid_access}")
            print(f"   payment_amount: {profile.payment_amount}")
            print(f"   free_access_start_time: {profile.free_access_start_time}")
        else:
            print("❌ No profile found!")
            
        # Check access level
        access_level = get_user_access_level(user)
        print(f"🎯 Access level: {access_level}")
        
        # Check specific permissions
        can_maps = can_access_map_view(user)
        can_lists = can_access_list_view(user)
        print(f"🗺️ Can access maps: {can_maps}")
        print(f"📋 Can access lists: {can_lists}")
        
        # Check if this should redirect
        if access_level in ['trial_expired', 'unauthenticated']:
            print(f"⚠️ WARNING: Access level '{access_level}' would trigger redirect!")
        else:
            print(f"✅ Access level '{access_level}' should NOT redirect")
            
    except User.DoesNotExist:
        print("❌ testuser3 not found - need to create it")
        
        # Create testuser3
        print("Creating testuser3...")
        user = User.objects.create_user(
            username='testuser3',
            email='testuser3@example.com',
            password='password123'
        )
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            has_paid_access=True,
            payment_amount=2.00,
            free_access_start_time=timezone.now()
        )
        
        print(f"✅ Created testuser3 with £{profile.payment_amount} payment")
        
        # Re-check access level
        access_level = get_user_access_level(user)
        print(f"🎯 New access level: {access_level}")

if __name__ == "__main__":
    debug_testuser3()