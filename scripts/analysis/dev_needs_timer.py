#!/usr/bin/env python
"""
Test the needs_timer template tag logic
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
from checker.templatetags.user_tags import needs_timer, has_paid_access
from django.utils import timezone

def test_user_timer_status():
    print("🧪 Testing Timer Logic for All Users")
    print("=" * 50)
    
    # Test all users
    for username in ['testuser', 'testuser2', 'testuser3', 'premiumuser']:
        try:
            user = User.objects.get(username=username)
            print(f"\n👤 User: {username}")
            print(f"   Authenticated: {user.is_authenticated}")
            print(f"   Has Profile: {hasattr(user, 'profile')}")
            
            if hasattr(user, 'profile') and user.profile:
                print(f"   Has Paid Access: {user.profile.has_paid_access}")
                print(f"   Free Access Start: {user.profile.free_access_start_time}")
                
                if user.profile.free_access_start_time:
                    elapsed = timezone.now() - user.profile.free_access_start_time
                    hours_remaining = 24 - (elapsed.total_seconds() / 3600)
                    print(f"   Hours Remaining: {hours_remaining:.1f}")
            
            print(f"   ⏱️ Needs Timer: {needs_timer(user)}")
            print(f"   💎 Has Paid Access: {has_paid_access(user)}")
            
            if needs_timer(user):
                print("   ❌ Will show timer/popup and redirect")
            else:
                print("   ✅ Will browse normally without restrictions")
                
        except User.DoesNotExist:
            print(f"\n❌ User '{username}' not found")
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    test_user_timer_status()