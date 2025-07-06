# Simple 2-Tier Access System Plan

## Overview
Simplified access control with just 2 user types for easier maintenance and clearer user experience.

## User Tiers

### Tier 1: Trial Users (Free)
- **Duration**: 24 hours per week
- **Reset Cycle**: 7 days from first registration
- **Access**: Full access to ALL features during trial period (maps, lists, everything)
- **Tracking**: 24 hours from first use after registration/reset
- **After expiry**: Redirect to payment page until next weekly reset
- **Auto-grant**: New users automatically get trial period on registration

### Tier 2: Full Access Users (Paid)
- **Price**: £5 for 1 year (annual subscription)
- **Access**: Unlimited access to all features
- **Duration**: 12 months from payment date
- **Renewal**: Manual renewal after 1 year expires

## Future Flexibility Note
The weekly trial system is designed to be easily changeable to usage-based limits in the future (e.g., based on number of searches, page views, or API calls) if needed for better resource management.

## Implementation Changes

### Simplifications
1. **Remove complex trial states** (trial_full, trial_limited)
2. **Remove £2 list-only tier** - too complex to maintain
3. **Single payment option** - just £5/year
4. **Weekly trial reset** (24 hours per 7-day cycle)
5. **No search limits** during trial - just time-based

### Database Changes
```sql
-- UserProfile fields needed:
- has_paid_access (boolean)
- paid_access_expiry_date (datetime) -- for 1-year renewals  
- trial_week_start (datetime) -- when current 7-day cycle started
- trial_first_use (datetime) -- when they first used trial this week
- trial_hours_used (decimal) -- hours used in current cycle
```

### Access Logic
```python
def get_user_access_level(user):
    if not user.is_authenticated:
        return 'unauthenticated'
    
    if user.is_superuser:
        return 'full'
    
    # Check paid access (£5/year)
    if user.profile.has_paid_access and user.profile.paid_access_expiry_date > now():
        return 'full'
    
    # Check weekly trial (24 hours per 7-day cycle)
    trial_hours_remaining = get_weekly_trial_hours_remaining(user)
    if trial_hours_remaining > 0:
        return 'trial'  # Full access during trial
    
    return 'trial_expired'  # Redirect to payment until next week
```

### Trial Logic Details
```python
def get_weekly_trial_hours_remaining(user):
    now = timezone.now()
    profile = user.profile
    
    # Check if we need to start a new 7-day cycle
    if not profile.trial_week_start or (now - profile.trial_week_start).days >= 7:
        # Reset for new week
        profile.trial_week_start = now
        profile.trial_first_use = None
        profile.trial_hours_used = 0
        profile.save()
    
    # If they haven't used trial this week yet, they have full 24 hours
    if not profile.trial_first_use:
        return 24.0
    
    # Calculate hours used since first use this week
    elapsed = (now - profile.trial_first_use).total_seconds() / 3600
    return max(0, 24.0 - elapsed)
```

### Benefits
- **Simpler to understand** - just trial vs paid
- **Easier to maintain** - fewer edge cases
- **Better user experience** - clearer pricing model
- **Less complex JavaScript** - no multiple timer types
- **Reduced support burden** - fewer user states to debug

## Migration Plan
1. Keep existing 4-tier system in `help-guide-improvements` branch
2. Implement 2-tier system in `simple-2tier-access` branch
3. Test thoroughly before deciding which to deploy
4. Can reference 4-tier code if more complexity needed later

## Implementation Tasks

### 1. Stripe Updates
- Update existing £5 product to be yearly subscription instead of one-time
- Or create new £5/year product if easier
- Remove £2 product option completely

### 2. Database Migration
- Add new fields to UserProfile: `trial_week_start`, `trial_first_use`, `trial_hours_used`
- Keep: `has_paid_access`, `paid_access_expiry_date`
- Remove complex trial tracking fields

### 3. Access Control Simplification
- `checker/access_control.py` - implement 2-tier logic with weekly trial
- Remove all 4-tier complexity (trial_full, trial_limited, list_only)
- Simple states: unauthenticated, trial, full, trial_expired

### 4. Frontend Updates
- `accounts/templates/accounts/account.html` - show weekly trial timer
- Remove complex tier-specific messaging
- Single payment option in payment selection
- Clear "£5/year" messaging

### 5. Registration Flow
- Auto-grant 24-hour weekly trial on user registration
- Start trial week counter immediately
- Begin usage timer on first site access

### Files to Modify
- `accounts/models.py` - add weekly trial fields
- `checker/access_control.py` - new 2-tier logic
- `accounts/views.py` - single £5/year payment flow
- `accounts/templates/accounts/payment_selection.html` - single option
- Templates - remove complex tier checking
- JavaScript - simplified weekly timer logic

## Current Branch Status
- **`help-guide-improvements`**: Complete 4-tier system (complex but working)
- **`simple-2tier-access`**: New simplified system (to be implemented)