"""
Simple 2-tier access control system for Capacity Market Registry

Tier 1: Trial users (Free)
- 1 week per month (resets monthly from registration)
- Full access to ALL features during trial period
- Timer starts on first use each month

Tier 2: Full paid users (£5/year)
- Unlimited access to everything
- 12-month duration from payment
"""

def get_user_access_level(user):
    """
    Determine user's access level in simplified 2-tier system
    
    Returns:
        'unauthenticated': Not logged in
        'trial': Has trial hours remaining this week (full access)
        'trial_expired': Trial used up, needs to pay or wait for reset
        'subscription_expired': Had paid access but subscription expired (no trial, must pay)
        'full': Paid £5/year - unlimited access
    """
    if not user.is_authenticated:
        return 'unauthenticated'
    
    # Admin/superusers get full access automatically
    if user.is_superuser or user.is_staff:
        return 'full'
    
    # Check if user has active paid access (£5/year)
    try:
        if hasattr(user, 'profile') and user.profile:
            # Check if they have paid access currently
            if user.profile.is_paid_access_active:
                return 'full'
            
            # Check if they PREVIOUSLY had paid access but it expired
            if user.profile.has_paid_access and not user.profile.is_paid_access_active:
                return 'subscription_expired'  # No trial available, must renew
            
            # Check weekly trial hours remaining (only for users who never paid)
            trial_hours = user.profile.get_weekly_trial_hours_remaining()
            if trial_hours > 0:
                return 'trial'  # Full access during trial
            else:
                return 'trial_expired'  # Need to pay or wait for weekly reset
    except AttributeError:
        # Handle case where user.profile doesn't exist or is None
        pass
    
    # No profile yet - should be created on registration
    return 'trial_expired'

def can_access_list_view(user):
    """Check if user can access list views (trial and full users can, subscription expired cannot)"""
    access_level = get_user_access_level(user)
    return access_level in ['trial', 'full']

def can_access_map_view(user):
    """Check if user can access map views (unauthenticated, trial, and full users can, subscription expired cannot)"""
    access_level = get_user_access_level(user)
    return access_level in ['unauthenticated', 'trial', 'full']

def can_access_premium_features(user):
    """Check if user can access any features (trial and full users can, subscription expired cannot)"""
    access_level = get_user_access_level(user)
    return access_level in ['trial', 'full']

def needs_weekly_timer(user):
    """Check if user needs weekly trial timer display"""
    access_level = get_user_access_level(user)
    return access_level == 'trial'

def is_trial_user(user):
    """Check if user is on trial (backward compatibility)"""
    access_level = get_user_access_level(user)
    return access_level == 'trial'

def start_trial_if_needed(user):
    """Start trial usage timer when user first accesses the site"""
    try:
        if hasattr(user, 'profile') and user.profile:
            user.profile.start_trial_usage()
    except AttributeError:
        # Handle case where user.profile doesn't exist
        pass

def get_access_message(user):
    """Get appropriate message for user's access level"""
    access_level = get_user_access_level(user)
    
    if access_level == 'unauthenticated':
        return {
            'title': 'Registration Required',
            'message': 'Register for 1 week free access per month to all features.',
            'action': 'Register Now',
            'url': '/accounts/register/'
        }
    elif access_level == 'trial_expired':
        return {
            'title': 'Trial Expired - Upgrade Now',
            'message': 'Your 1 week monthly trial is used up. Get £5/year unlimited access or wait for monthly reset.',
            'action': 'Get Full Access',
            'url': '/accounts/payment_selection/'
        }
    elif access_level == 'subscription_expired':
        return {
            'title': 'Subscription Expired - Renew Required',
            'message': 'Your £5/year subscription has expired. Renew now to restore unlimited access. No trial available.',
            'action': 'Renew Subscription',
            'url': '/accounts/payment_required/'
        }
    else:
        return None  # Trial and full users don't need blocking messages