"""
Decorators for simplified 2-tier access control
"""
from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages
from .. import access_control

def access_required(view_func):
    """
    Decorator to require access for any protected view in 2-tier system
    
    - Unauthenticated users: Redirected to register  
    - Trial expired users: Redirected to payment selection
    - Trial and full users: Access granted
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_access_level = access_control.get_user_access_level(request.user)
        
        # Start trial timer if user is accessing for first time this week
        if user_access_level == 'trial':
            access_control.start_trial_if_needed(request.user)
        
        # In 2-tier system, allow unauthenticated users to browse with 5-minute timer
        # Only block trial_expired users
        if user_access_level == 'trial_expired':
            return redirect('accounts:payment_required')  # Use named URL pattern
        
        # Allow unauthenticated, trial, and full users to proceed
        # (unauthenticated users have their 5-minute timer managed by JavaScript)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

# Backward compatibility aliases
map_access_required = access_required  # Maps and lists both need same access now

def premium_feature_required(feature_name="Premium Feature"):
    """
    Decorator to require access for specific features (same as access_required in 2-tier)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # In 2-tier system, all features have same access requirements
            return access_required(view_func)(request, *args, **kwargs)
        
        return wrapper
    
    return decorator