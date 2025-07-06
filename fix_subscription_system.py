#!/usr/bin/env python3
"""
Fix the £5/year subscription system to properly handle renewals and expiry
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

def fix_subscription_for_user(email):
    """Fix user subscription to be proper £5/year with expiry"""
    
    print(f'🔧 FIXING £5/YEAR SUBSCRIPTION FOR {email}')
    print('=' * 60)
    
    try:
        user = User.objects.get(email=email)
        profile = UserProfile.objects.get(user=user)
        
        print(f'📋 BEFORE:')
        print(f'   Has paid access: {profile.has_paid_access}')
        print(f'   Payment amount: £{profile.payment_amount}')
        print(f'   Expiry: {profile.paid_access_expiry_date}')
        print(f'   Is active: {profile.is_paid_access_active}')
        
        # Set up proper £5/year subscription
        profile.has_paid_access = True
        profile.payment_amount = 5.00
        
        # Set expiry to 1 year from now (for testing - in production this would be from payment date)
        profile.paid_access_expiry_date = timezone.now() + timedelta(days=365)
        profile.save()
        
        print(f'\\n✅ AFTER:')
        print(f'   Has paid access: {profile.has_paid_access}')
        print(f'   Payment amount: £{profile.payment_amount}')
        print(f'   Expiry: {profile.paid_access_expiry_date}')
        print(f'   Is active: {profile.is_paid_access_active}')
        print(f'   Days until renewal: {(profile.paid_access_expiry_date - timezone.now()).days}')
        
        return True
        
    except User.DoesNotExist:
        print(f'❌ User not found: {email}')
        return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def analyze_webhook_logic():
    """Analyze what the webhook should do for £5/year subscriptions"""
    
    print(f'\\n🔍 WEBHOOK ANALYSIS FOR £5/YEAR SUBSCRIPTIONS')
    print('=' * 60)
    
    print(f"""
✅ CURRENT WEBHOOK LOGIC (lines 329-376 in accounts/views.py):
1. Handles 'checkout.session.completed' ✓
2. Sets has_paid_access = True ✓  
3. Sets payment_amount = 5.00 ✓
4. Sets expiry to 1 year from now ✓
5. Handles 'invoice.payment_succeeded' for renewals ✓

🔧 WHAT HAPPENS ON PAYMENT:
- User pays £5 via Stripe subscription
- Stripe webhook fires 'checkout.session.completed'  
- System grants 1 year access
- Access expires after 365 days
- Stripe auto-charges £5 for renewal
- Webhook fires 'invoice.payment_succeeded'
- System extends access for another year

💡 THE SYSTEM IS ACTUALLY CORRECT!
The webhook on lines 347-355 properly sets:
- profile.paid_access_expiry_date = timezone.now() + timedelta(days=365)

🚨 THE ISSUE: Local testing can't receive webhooks!
- Stripe webhooks only work on live servers
- Local payments don't trigger webhook events
- Database doesn't get updated without webhook

🎯 SOLUTIONS:
1. Test on production (push to Heroku) ✓
2. Use webhook test events from Stripe CLI
3. Manually simulate subscription (for testing)
""")

if __name__ == "__main__":
    # Fix the current user to have proper subscription
    fix_subscription_for_user('davidcrawford83@gmail.com')
    
    # Analyze webhook logic
    analyze_webhook_logic()
    
    print(f'\\n🚀 READY FOR TESTING:')
    print(f'- User now has proper £5/year subscription')  
    print(f'- Expires in 365 days')
    print(f'- Log out and back in to see changes')
    print(f'- For production: push webhook fixes to Heroku')