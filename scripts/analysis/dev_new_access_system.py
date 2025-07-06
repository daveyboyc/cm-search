#!/usr/bin/env python
"""
Test the new access control system
"""
import os
import sys
import django

sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from checker.access_control import get_user_access_level, can_access_list_view, can_access_map_view, needs_map_timer

def test_new_access_system():
    print("🚀 Testing New Access Control System")
    print("=" * 60)
    
    # Test each user type
    for username in ['testuser', 'testuser2', 'testuser3', 'premiumuser']:
        try:
            user = User.objects.get(username=username)
            access_level = get_user_access_level(user)
            
            print(f"\n👤 {username}")
            print(f"   Access Level: {access_level}")
            print(f"   Can Access Lists: {can_access_list_view(user)}")
            print(f"   Can Access Maps: {can_access_map_view(user)}")
            print(f"   Needs Map Timer: {needs_map_timer(user)}")
            
            # Show behavior
            if access_level == 'trial':
                print("   🎯 Behavior: 24h full access + 5min map timer")
            elif access_level == 'trial_expired':
                print("   🎯 Behavior: Must choose £2 (lists) or £5 (full)")
            elif access_level == 'list_only':
                print("   🎯 Behavior: Lists only, no maps")
            elif access_level == 'full':
                print("   🎯 Behavior: Unlimited access to everything")
            elif access_level == 'unauthenticated':
                print("   🎯 Behavior: Must register first")
                
        except User.DoesNotExist:
            print(f"\n❌ {username} not found")
    
    print("\n" + "=" * 60)
    print("✅ New access system ready!")
    print("\n🎯 Expected Flow:")
    print("1. Register → 24 hours full access")
    print("2. Access maps → 5-minute timer starts")
    print("3. After 5 minutes → Maps locked, lists still work")
    print("4. Payment options: £2 (lists only) or £5 (full access)")

if __name__ == "__main__":
    test_new_access_system()