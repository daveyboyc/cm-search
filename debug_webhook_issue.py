#!/usr/bin/env python3
"""
Comprehensive webhook debugging
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.conf import settings
import requests

def debug_webhook_setup():
    print('🔍 WEBHOOK DEBUGGING - COMPREHENSIVE CHECK')
    print('=' * 60)
    
    # Check 1: Environment Variables
    print('1. ENVIRONMENT VARIABLES:')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    stripe_secret = getattr(settings, 'STRIPE_SECRET_KEY', None)
    
    if webhook_secret:
        print(f'   ✅ STRIPE_WEBHOOK_SECRET: {webhook_secret[:10]}...{webhook_secret[-5:]}')
    else:
        print(f'   ❌ STRIPE_WEBHOOK_SECRET: Not configured!')
        
    if stripe_secret:
        print(f'   ✅ STRIPE_SECRET_KEY: {stripe_secret[:10]}...{stripe_secret[-5:]}')
    else:
        print(f'   ❌ STRIPE_SECRET_KEY: Not configured!')
    
    # Check 2: URL Accessibility
    print(f'\n2. WEBHOOK ENDPOINT TEST:')
    webhook_url = 'https://capacitymarket.co.uk/account/stripe/webhook/'
    
    try:
        # Test GET (should be 405)
        response = requests.get(webhook_url, timeout=10)
        print(f'   GET {webhook_url}')
        print(f'   Status: {response.status_code} (should be 405)')
        
        # Test POST (should be 400 without proper signature)
        response = requests.post(
            webhook_url, 
            json={'test': 'data'}, 
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f'   POST {webhook_url}')
        print(f'   Status: {response.status_code} (should be 400 - signature verification fail)')
        
    except Exception as e:
        print(f'   ❌ Error testing endpoint: {e}')
    
    # Check 3: Recent Users Analysis
    print(f'\n3. RECENT PAYMENTS ANALYSIS:')
    from django.contrib.auth.models import User
    from accounts.models import UserProfile
    from django.utils import timezone
    from datetime import timedelta
    
    recent_users = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(hours=3)
    ).order_by('-date_joined')
    
    payment_users = []
    for user in recent_users:
        try:
            profile = UserProfile.objects.get(user=user)
            minutes_ago = (timezone.now() - user.date_joined).total_seconds() / 60
            
            print(f'   📧 {user.email}')
            print(f'      Joined: {minutes_ago:.0f} minutes ago')
            print(f'      Paid access: {profile.has_paid_access}')
            print(f'      Payment amount: £{profile.payment_amount}')
            
            # If they joined recently but don't have paid access, they likely paid
            if not profile.has_paid_access and minutes_ago < 60:
                payment_users.append(user.email)
                
        except UserProfile.DoesNotExist:
            print(f'   📧 {user.email} (no profile)')
    
    # Check 4: Webhook Failure Scenarios
    print(f'\n4. LIKELY WEBHOOK FAILURE REASONS:')
    
    if not webhook_secret:
        print(f'   🚨 CRITICAL: No webhook secret configured')
        print(f'      → Webhooks will always fail signature verification')
        
    if payment_users:
        print(f'   🚨 ISSUE: {len(payment_users)} recent users without paid access')
        print(f'      → Suggests webhooks are not reaching/processing correctly')
        
    print(f'\n5. STRIPE WEBHOOK CHECKLIST:')
    print(f'   ✅ URL: https://capacitymarket.co.uk/account/stripe/webhook/')
    print(f'   ✅ Events: checkout.session.completed, invoice.payment_succeeded')
    print(f'   ❓ Secret: Must match your Heroku STRIPE_WEBHOOK_SECRET')
    print(f'   ❓ Status: Must be "Enabled" in Stripe dashboard')
    
    print(f'\n🎯 RECOMMENDED ACTIONS:')
    print(f'1. Check webhook secret matches between Stripe and Heroku')
    print(f'2. Verify webhook is enabled in Stripe dashboard')
    print(f'3. Look at "Recent deliveries" in Stripe webhook dashboard')
    print(f'4. Check if webhooks are being sent but failing')

if __name__ == "__main__":
    debug_webhook_setup()