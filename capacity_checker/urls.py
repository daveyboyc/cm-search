"""
URL configuration for capacity_checker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Import settings
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse, JsonResponse
from accounts.views import stripe_webhook_view  # Import webhook view

from django.views.decorators.cache import cache_page
from checker.utils.smart_cache import long_cache
from checker.sitemaps import StaticSitemap, LocationSitemap, TechnologySitemap, CompanySitemap, GuidesSitemap
from checker.views_maintenance import maintenance_view
import sys
import os

print("DEBUG: Loading main urls.py", file=sys.stderr)

# Sitemap configuration
sitemaps = {
    'static': StaticSitemap,
    'guides': GuidesSitemap,
    'locations': LocationSitemap,
    'technologies': TechnologySitemap,
    'companies': CompanySitemap,
}

@long_cache  # 10 minute smart cache
def ads_txt(request):
    """Serve ads.txt file for AdSense verification"""
    # Use the project root static directory (parent of BASE_DIR) to find ads.txt
    ads_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'static', 'ads.txt')
    try:
        with open(ads_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/plain')
    except FileNotFoundError:
        # Return the required AdSense entry if file not found
        content = "google.com, pub-3181446379162312, DIRECT, f08c47fec0942fa0"
        return HttpResponse(content, content_type='text/plain')

@long_cache  # 10 minute smart cache
def robots_txt(request):
    """Serve robots.txt file"""
    # robots.txt is in the parent directory's static folder
    robots_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'static', 'robots.txt')
    try:
        with open(robots_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/plain')
    except FileNotFoundError as e:
        print(f"DEBUG: robots.txt not found at {robots_path}, error: {e}", file=sys.stderr)
        # Fallback robots.txt if file not found
        content = """User-agent: *
Allow: /
Crawl-delay: 10
Sitemap: https://www.capacitymarket.co.uk/sitemap.xml
"""
        return HttpResponse(content, content_type='text/plain')

@long_cache  # 10 minute smart cache
def ai_plugin_json(request):
    """Serve ai-plugin.json file for AI/ChatGPT discoverability"""
    ai_plugin_path = os.path.join(settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static'), '.well-known', 'ai-plugin.json')
    try:
        with open(ai_plugin_path, 'r') as f:
            import json
            content = json.load(f)
        return JsonResponse(content)
    except FileNotFoundError:
        # Fallback ai-plugin.json if file not found
        content = {
            "schema_version": "v1",
            "name_for_human": "Capacity Market Search",
            "name_for_model": "capacity_market_search",
            "description_for_human": "Search UK Capacity Market auction data, companies, technologies, and locations.",
            "description_for_model": "UK Capacity Market database with power generation facilities, companies, technologies, and auction results.",
            "auth": {"type": "none"},
            "api": {"type": "openapi", "url": "https://capacitymarket.co.uk/.well-known/openapi.json"},
            "logo_url": "https://capacitymarket.co.uk/static/images/favicon.png"
        }
        return JsonResponse(content)

urlpatterns = [
    path('ads.txt', ads_txt, name='ads_txt'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('.well-known/ai-plugin.json', ai_plugin_json, name='ai_plugin_json'),
    path('maintenance/', maintenance_view, name='maintenance'),  # Maintenance page
    path('admin/', admin.site.urls),
    path('monitoring/', include('monitoring.urls')),
    path('accounts/', include('accounts.urls')),
    # Add direct webhook URL that Stripe is currently configured to use
    path('account/stripe-webhook/', stripe_webhook_view, name='stripe_webhook_direct'),
    path('trades/', include('trades.urls')),  # Trading bulletin board
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    path("", include("checker.urls")),  # Must be last due to catch-all patterns
]

# Error handlers
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

# Add Debug Toolbar URLs only in DEBUG mode
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
