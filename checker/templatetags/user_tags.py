from django import template
from ..access_control import get_user_access_level, needs_weekly_timer

register = template.Library()

@register.filter
def has_paid_access(user):
    """Check if user has paid access (£5/year)"""
    if user is None:
        return False
    access_level = get_user_access_level(user)
    return access_level == 'full'

@register.filter
def has_full_access(user):
    """Check if user has full access (£5/year) - same as has_paid_access in 2-tier"""
    if user is None:
        return False
    access_level = get_user_access_level(user)
    return access_level == 'full'

@register.filter
def has_list_access(user):
    """Check if user can access lists (both trial and full users can)"""
    if user is None:
        return False
    from ..access_control import can_access_list_view
    return can_access_list_view(user)

@register.filter
def needs_timer(user):
    """Check if user needs the weekly trial timer"""
    if user is None:
        return False
    return needs_weekly_timer(user)

@register.filter
def user_access_level(user):
    """Get user's access level"""
    if user is None:
        return 'anonymous'
    return get_user_access_level(user)

@register.filter
def can_access_maps(user):
    """Check if user can access map features (both trial and full users can)"""
    if user is None:
        return False
    from ..access_control import can_access_map_view
    return can_access_map_view(user)

@register.filter
def is_trial_user(user):
    """Check if user is on trial"""
    if user is None:
        return False
    access_level = get_user_access_level(user)
    return access_level == 'trial'

@register.filter
def is_trial_expired(user):
    """Check if user's trial is expired"""
    if user is None:
        return False
    access_level = get_user_access_level(user)
    return access_level == 'trial_expired'

# Legacy filters for backward compatibility
@register.filter
def is_trial_full_user(user):
    """LEGACY: Check if user is on trial - all trial users have full access in 2-tier"""
    if user is None:
        return False
    return is_trial_user(user)

@register.filter
def is_trial_limited_user(user):
    """LEGACY: No limited trial users in 2-tier system"""
    return False