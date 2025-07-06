from django.urls import path, include
from django.conf import settings  # Import settings

# Main URL Patterns
urlpatterns = [
    path("", include("checker.urls")),
    path("accounts/", include("accounts.urls")), # Include accounts URLs (Ensuring this is active)
]

# Add Debug Toolbar URLs only in DEBUG mode
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns 