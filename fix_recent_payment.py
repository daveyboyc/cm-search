#!/usr/bin/env python3
"""
Manually grant access for recent payment that webhook missed
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone
from datetime import timedelta

def fix_recent_payment():
    """Find and fix recent payment that didn't trigger webhook"""
    
    print('🔍 FIXING RECENT PAYMENT - WEBHOOK MISSED')
    print('=' * 60)
    
    # Find most recent user (likely the one who just paid)
    recent_users = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(hours=1)
    ).order_by('-date_joined')
    
    if not recent_users.exists():
        print('❌ No users registered in last hour')
        return
    
    print(f'📋 RECENT USERS (last hour):')
    for i, user in enumerate(recent_users[:5], 1):
        try:
            profile = UserProfile.objects.get(user=user)
            print(f'{i}. {user.email} (joined {user.date_joined})')
            print(f'   Has paid access: {profile.has_paid_access}')
            print(f'   Payment amount: £{profile.payment_amount}')
            print(f'   Trial hours remaining: {profile.get_weekly_trial_hours_remaining():.1f}')
            print()
        except UserProfile.DoesNotExist:
            print(f'{i}. {user.email} (NO PROFILE)')
    
    # Ask which user to fix
    print('🔧 MANUAL FIX NEEDED:')
    email = input('Enter email of user who paid £5: ').strip()
    
    if not email:
        print('❌ No email provided')
        return
    
    try:
        user = User.objects.get(email=email)
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        print(f'\\n👤 FIXING USER: {user.email}')
        print(f'   Before: has_paid_access={profile.has_paid_access}')
        
        # Grant £5/year subscription
        profile.has_paid_access = True
        profile.payment_amount = 5.00
        profile.paid_access_expiry_date = timezone.now() + timedelta(days=365)
        profile.save()
        
        print(f'   After: has_paid_access={profile.has_paid_access}')
        print(f'   Payment: £{profile.payment_amount}/year')
        print(f'   Expires: {profile.paid_access_expiry_date.strftime("%Y-%m-%d")}')
        print(f'   Days remaining: {(profile.paid_access_expiry_date - timezone.now()).days}')
        
        print(f'\\n✅ SUCCESS: User should now have full access!')
        print(f'   Tell them to log out and log back in')
        
    except User.DoesNotExist:
        print(f'❌ User not found: {email}')

if __name__ == "__main__":
    fix_recent_payment()