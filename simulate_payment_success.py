#!/usr/bin/env python3
"""
Simulate a successful £5 payment for testing locally
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

def simulate_payment_success(email, amount=5.0):
    """Simulate a successful payment"""
    
    print(f'💳 SIMULATING £{amount} PAYMENT SUCCESS FOR {email}')
    print('=' * 60)
    
    try:
        user = User.objects.get(email=email)
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if created:
            print(f'✅ Created new UserProfile for {user.username}')
        else:
            print(f'✅ Found existing UserProfile for {user.username}')
        
        # Simulate successful payment processing
        profile.has_paid_access = True
        profile.payment_amount = amount
        profile.paid_access_expiry_date = None  # Perpetual access
        profile.save()
        
        print(f'✅ Payment processed successfully!')
        print(f'   Amount: £{amount}')
        print(f'   Access: Full (perpetual)')
        print(f'   User: {user.username} ({user.email})')
        
        return True
        
    except User.DoesNotExist:
        print(f'❌ User not found: {email}')
        return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    # Test with your email
    simulate_payment_success('davidcrawford83@gmail.com')