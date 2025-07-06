#!/usr/bin/env python
"""
Clear timer lockout for testing
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("""
⚠️  LOCKOUT CLEARING INSTRUCTIONS
================================

To clear the timer and map trial for testuser:

1. Open browser developer tools (F12)
2. Go to Application/Storage tab
3. Find Session Storage for localhost:8000
4. Delete ALL of these keys:
   - timerStartTime
   - timerLockout (old key)
   - mapTrialExpired (new key)
   
5. Refresh the page

The timer system is now configured to:
- Only show timer/popup on MAP pages
- Allow free browsing of list views
- Give 10-MINUTE trial when accessing maps
- Warning popup in last 30 seconds
- Redirect to payment page only after timer expires on map pages

Test accounts:
- testuser / testpass123 (free user)
- premiumuser / testpass123 (premium user)
""")