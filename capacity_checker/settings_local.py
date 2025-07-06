"""
Local development settings override
"""
from .settings import *

# Use console email backend for development
EMAIL_BACKEND = 'accounts.backends.LoggingEmailBackend'

# Or use Django's console backend
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Override site settings for local development
SITE_SCHEME = 'http'
SITE_DOMAIN = 'localhost:8000'

print("✅ Using local development settings with console email backend")