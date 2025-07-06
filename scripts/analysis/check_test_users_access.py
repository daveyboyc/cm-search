#!/usr/bin/env python3
"""
Check access levels for test users
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from checker.access_control import get_user_access_level, can_access_map_view, can_access_list_view

def check_user_access(username):
    """Check access level for a specific user"""
    try:
        user = User.objects.get(username=username)
        access_level = get_user_access_level(user)
        can_maps = can_access_map_view(user)
        can_lists = can_access_list_view(user)
        
        payment_amount = "N/A"
        has_paid = False
        if hasattr(user, 'profile') and user.profile:
            payment_amount = f"£{user.profile.payment_amount}" if user.profile.payment_amount else "£0.00"
            has_paid = user.profile.has_paid_access
        
        print(f"""
👤 {username}:
   Access Level: {access_level}
   Can Access Maps: {can_maps}
   Can Access Lists: {can_lists}
   Payment Amount: {payment_amount}
   Has Paid Access: {has_paid}
   Staff/Admin: {user.is_staff or user.is_superuser}
        """)
        
    except User.DoesNotExist:
        print(f"❌ User '{username}' not found")

if __name__ == "__main__":
    print("🔍 Checking Test User Access Levels")
    print("=" * 50)
    
    test_users = ['testuser', 'testuser2', 'testuser3']
    
    for username in test_users:
        check_user_access(username)
    
    # Also check if there's an admin user
    admin_users = User.objects.filter(is_superuser=True)
    if admin_users.exists():
        admin_user = admin_users.first()
        print(f"\n👑 Admin User Example:")
        check_user_access(admin_user.username)
    
    print("\n🎯 Expected Results:")
    print("   testuser/testuser2: trial_limited (maps blocked)")
    print("   testuser3: list_only (maps blocked, unlimited lists)")
    print("   admin users: full (unlimited everything)")