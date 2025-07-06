# URL Namespace Issues - Common Errors to Avoid

## ⚠️ CRITICAL: URLs Use `/accounts/` NOT `/account/`

**RECURRING ERROR**: Using `/account/` instead of `/accounts/` for authentication URLs.

### Correct URLs:
- ✅ `/accounts/login/`
- ✅ `/accounts/logout/`
- ✅ `/accounts/register/`
- ✅ `/accounts/must-register/`
- ✅ `/accounts/payment-required/`
- ✅ `/accounts/payment-selection/`
- ✅ `/accounts/account/` (account management page)

### Incorrect URLs (will cause 404s):
- ❌ `/account/login/`
- ❌ `/account/logout/`
- ❌ `/account/register/`
- ❌ `/account/must-register/`
- ❌ `/account/payment-required/`

## Template URL References

### Correct Template Syntax:
```django
{% url 'accounts:login' %}
{% url 'accounts:logout' %}
{% url 'accounts:register' %}
{% url 'accounts:must_register' %}
```

### Incorrect Template Syntax (will cause NoReverseMatch):
```django
{% url 'login' %}  ❌ Missing namespace
{% url 'logout' %} ❌ Missing namespace
```

## Files That Have Been Fixed:

### Templates:
- `accounts/templates/registration/logged_out.html`
- `checker/templates/checker/includes/map_navbar.html`
- `accounts/templates/accounts/register.html`
- `accounts/templates/accounts/must_register.html`
- `templates/registration/password_reset_done.html`
- `templates/registration/password_reset_form.html`
- `templates/registration/password_reset_complete.html`
- `checker/templates/checker/includes/welcome_notice.html`

### Middleware:
- `checker/middleware/access_control.py` - Fixed public_urls list

## Root Cause

The accounts app is configured with:
```python
# accounts/urls.py
app_name = 'accounts'  # This creates the namespace

# capacity_checker/urls.py  
path('accounts/', include('accounts.urls')),  # This creates the URL prefix
```

This means:
- URL namespace: `accounts:`
- URL prefix: `/accounts/`
- Full URL example: `/accounts/login/` with name `accounts:login`

## Prevention

Always check these locations when adding authentication-related features:

1. **Templates**: Use `{% url 'accounts:view_name' %}`
2. **JavaScript**: Use `/accounts/` prefix for redirects
3. **Middleware**: Use `/accounts/` in public_urls lists
4. **Views**: Use `reverse('accounts:view_name')` for redirects

## Testing

To verify URLs work correctly:
- Test logout functionality 
- Test registration flow
- Test password reset flow
- Check that timer expiration redirects to `/accounts/must-register/`