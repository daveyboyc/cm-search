import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email settings for Zoho
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_PORT = 587  # Use 587 for TLS
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False # TLS is generally preferred over SSL
EMAIL_HOST_USER = 'hello@capacitymarket.co.uk'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD') # Get password from environment
DEFAULT_FROM_EMAIL = 'Capacity Market <hello@capacitymarket.co.uk>'
SERVER_EMAIL = 'hello@capacitymarket.co.uk' # Used for error emails to admins

# Ensure EMAIL_HOST_PASSWORD is set
if not EMAIL_HOST_PASSWORD:
    print("Warning: EMAIL_HOST_PASSWORD environment variable not set.")

# ... rest of your settings ... 