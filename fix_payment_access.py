#!/usr/bin/env python3
"""
Fix payment access for user
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile

def fix_payment_access():
    print('🔍 CHECKING PAYMENT STATUS FOR davidcrawford83@gmail.com')
    print('=' * 60)
    
    try:
        user = User.objects.get(email='davidcrawford83@gmail.com')
        print(f'✅ User found: {user.username} ({user.email})')
        print(f'   User ID: {user.id}')
        print(f'   Date joined: {user.date_joined}')
        print(f'   Is active: {user.is_active}')
        
        try:
            profile = UserProfile.objects.get(user=user)
            print(f'\n📋 USER PROFILE:')
            print(f'   Has paid access: {profile.has_paid_access}')
            print(f'   Payment amount: £{profile.payment_amount}')
            print(f'   Paid access expiry: {profile.paid_access_expiry_date}')
            print(f'   Is paid access active: {profile.is_paid_access_active}')
            print(f'   Trial hours remaining: {profile.get_weekly_trial_hours_remaining():.1f}')
            
            # Check if payment amount is set but has_paid_access not updated
            if profile.payment_amount and profile.payment_amount >= 5.0:
                if not profile.has_paid_access:
                    print(f'\n🚨 ISSUE FOUND: Payment recorded (£{profile.payment_amount}) but has_paid_access is False')
                    print(f'   Updating now...')
                    
                    profile.has_paid_access = True
                    profile.paid_access_expiry_date = None  # Perpetual access
                    profile.save()
                    print(f'✅ Updated has_paid_access to: True')
                    print(f'✅ User should now have full access')
                else:
                    print(f'\n✅ Payment and access status are correct')
            else:
                print(f'\n⚠️  No payment recorded or amount < £5')
                # Set payment manually if needed
                print(f'   Setting payment to £5.00 and access to paid...')
                profile.payment_amount = 5.0
                profile.has_paid_access = True
                profile.paid_access_expiry_date = None
                profile.save()
                print(f'✅ Manually set payment and access status')
                
        except UserProfile.DoesNotExist:
            print(f'\n❌ No UserProfile found - creating one...')
            profile = UserProfile.objects.create(
                user=user,
                has_paid_access=True,
                payment_amount=5.0,
                paid_access_expiry_date=None
            )
            print(f'✅ Created UserProfile with paid access')
            
    except User.DoesNotExist:
        print(f'❌ User not found with email: davidcrawford83@gmail.com')
        
        # Check if user exists with different email
        users = User.objects.filter(username__icontains='davidcrawford')
        if users.exists():
            print(f'\n🔍 Found similar users:')
            for u in users[:5]:
                print(f'   {u.username} - {u.email}')
                
    print(f'\n' + '=' * 60)
    print(f'✅ Payment access check complete')
    print(f'   User should log out and log back in to see changes')

if __name__ == "__main__":
    fix_payment_access()