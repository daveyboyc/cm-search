#!/usr/bin/env python3
"""
Simple test for access control without Django
"""

# Simulate the access control logic
def get_user_access_level_simple(user_data):
    """
    Simulate the access control logic
    """
    # Admin/superusers get full access automatically
    if user_data.get('is_superuser') or user_data.get('is_staff'):
        return 'full'
    
    # Check payment status
    profile = user_data.get('profile', {})
    if profile.get('has_paid_access'):
        # Check payment amount to determine access level
        payment_amount = profile.get('payment_amount', 0)
        if payment_amount >= 5:
            return 'full'
        elif payment_amount >= 2:
            return 'list_only'
        return 'full'  # Default for existing paid users
    
    # Check if still in 24-hour trial
    if profile.get('free_access_start_time'):
        # Simulate: within 24 hours
        trial_active = True  # Assume within trial period for testing
        if trial_active:
            # Simulate map usage check
            map_usage_expired = True  # Currently set to True in the code
            if map_usage_expired:
                return 'trial_limited'  # Maps expired but lists still work
            else:
                return 'trial_full'     # Full trial access
    
    # Trial expired, needs to pay
    return 'trial_expired'

# Test testuser3 configuration
testuser3_data = {
    'username': 'testuser3',
    'is_superuser': False,
    'is_staff': False,
    'profile': {
        'has_paid_access': True,
        'payment_amount': 2.00,
        'free_access_start_time': '2024-01-01'  # Has a trial start time
    }
}

print("🧪 Testing testuser3 access logic:")
print(f"User data: {testuser3_data}")

access_level = get_user_access_level_simple(testuser3_data)
print(f"Access level result: {access_level}")

if access_level == 'list_only':
    print("✅ CORRECT: Should be list_only")
else:
    print(f"❌ WRONG: Expected 'list_only', got '{access_level}'")

# Test what happens if we remove free_access_start_time
testuser3_no_trial = testuser3_data.copy()
testuser3_no_trial['profile'] = testuser3_no_trial['profile'].copy()
testuser3_no_trial['profile']['free_access_start_time'] = None

print(f"\n🧪 Testing without trial start time:")
access_level2 = get_user_access_level_simple(testuser3_no_trial)
print(f"Access level result: {access_level2}")