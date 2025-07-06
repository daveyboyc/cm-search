#!/usr/bin/env python3
"""
Fix the payment system to handle one-time £5 payments
"""

print("""
🔧 PAYMENT SYSTEM ANALYSIS & FIX NEEDED

CURRENT ISSUE:
- Your payment system is set to mode='subscription' 
- But you're doing one-time £5 payments
- Webhook only handles subscription events
- One-time payments generate 'payment_intent.succeeded' events

TO FIX FOR PRODUCTION:

1. CHANGE PAYMENT MODE in accounts/views.py:
   Line 275: mode='subscription'  ->  mode='payment'

2. ADD WEBHOOK HANDLER for one-time payments:
   Add handler for 'payment_intent.succeeded' event

3. UPDATE STRIPE PRODUCT:
   Create a one-time £5 product instead of subscription

4. SET WEBHOOK ENDPOINT in Stripe Dashboard:
   Point to: https://capacitymarket.co.uk/accounts/stripe/webhook/

FOR LOCAL TESTING:
Run: python simulate_payment_success.py
This will manually grant access without needing real payments.

RECOMMENDED CHANGES:
""")

changes_needed = """
# In accounts/views.py, change line 275:
mode='payment',  # One-time payment instead of subscription

# Add this webhook handler after line 376:
elif event['type'] == 'payment_intent.succeeded':
    payment_intent = event['data']['object']
    metadata = payment_intent.metadata
    user_id = metadata.get('user_id')
    
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Grant full access for £5 one-time payment
            profile.has_paid_access = True
            profile.payment_amount = 5.00
            profile.paid_access_expiry_date = None  # Perpetual
            profile.save()
            
            logger.info(f"One-time payment processed for user {user.username}")
            
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found for payment_intent")

# Also update the line_items to use a one-time price:
line_items=[
    {
        'price_data': {
            'currency': 'gbp',
            'product_data': {
                'name': 'Full Access - Capacity Market Registry',
                'description': 'Lifetime access to all features',
            },
            'unit_amount': 500,  # £5.00 in pence
        },
        'quantity': 1,
    },
],
"""

print(changes_needed)

print("""
🚀 QUICK SOLUTION FOR TESTING:
Run this to grant access without payment:
python simulate_payment_success.py davidcrawford83@gmail.com

Then test your registration flow!
""")