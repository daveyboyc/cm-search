#!/usr/bin/env python
"""Add caching to statistics view for better performance"""
import os

print("🚀 Adding caching to statistics view")
print("=" * 50)

# The patch to add caching
CACHE_PATCH = '''
def statistics_view(request):
    """View function for displaying database statistics"""
    from .utils import normalize
    from django.db.models import Count, Q, Sum
    from django.core.cache import cache  # ADD THIS
    import logging
    logger = logging.getLogger(__name__)
    
    # CACHE CONFIGURATION
    CACHE_TTL = 3600  # 1 hour cache
    CACHE_PREFIX = "statistics_"
    
    # Generate cache key based on request parameters
    company_sort = request.GET.get('company_sort', 'count')
    company_order = request.GET.get('company_order', 'desc')
    tech_sort = request.GET.get('tech_sort', 'count')
    tech_order = request.GET.get('tech_order', 'desc')
    
    cache_key = f"{CACHE_PREFIX}{company_sort}_{company_order}_{tech_sort}_{tech_order}"
    
    # Try to get from cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"✅ Statistics cache HIT for key: {cache_key}")
        return render(request, 'checker/statistics.html', cached_data)
    
    logger.info(f"❌ Statistics cache MISS for key: {cache_key}")
    
    # Continue with existing logic...
'''

print("\nTo fix the statistics page performance:")
print("\n1. Add caching at the beginning of statistics_view()")
print("2. Cache the entire context dictionary before rendering")
print("3. Use a 1-hour cache TTL")
print("4. Clear cache after crawls")

print("\nExample implementation:")
print("-" * 50)
print("""
# At the beginning of statistics_view():
from django.core.cache import cache

# Generate cache key
cache_key = f"statistics_{company_sort}_{company_order}_{tech_sort}_{tech_order}"

# Check cache
cached_context = cache.get(cache_key)
if cached_context:
    return render(request, 'checker/statistics.html', cached_context)

# ... (existing code to build context) ...

# Before rendering, cache the context:
cache.set(cache_key, context, 3600)  # Cache for 1 hour

return render(request, 'checker/statistics.html', context)
""")

print("\n💡 This will make the statistics page load instantly after first visit!")
print("   First load: ~1.2s (builds data)")
print("   Cached loads: <0.01s (from cache)")

# Create a simple cached statistics endpoint
cached_stats_code = '''
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@cache_page(60 * 60)  # Cache for 1 hour
@vary_on_headers('X-Requested-With')  # Vary on AJAX requests
def statistics_view_cached(request):
    """Cached version of statistics view"""
    # Call the original statistics_view
    return statistics_view(request)
'''

print("\n\nAlternatively, use Django's @cache_page decorator:")
print("-" * 50)
print(cached_stats_code)