#!/usr/bin/env python
"""Patch the statistics view to add caching"""
import os
import sys

# Read the views.py file
views_file = 'checker/views.py'
with open(views_file, 'r') as f:
    content = f.read()

# Check if caching is already added
if 'statistics_cache_key' in content:
    print("✅ Caching already added to statistics view!")
    sys.exit(0)

print("🔧 Patching statistics view to add caching...")

# Find the statistics_view function
import_section = """def statistics_view(request):
    \"\"\"View function for displaying database statistics\"\"\"
    from .utils import normalize
    from django.db.models import Count, Q, Sum # Ensure Sum is imported
    import logging # Add logging
    logger = logging.getLogger(__name__)"""

replacement = """def statistics_view(request):
    \"\"\"View function for displaying database statistics\"\"\"
    from .utils import normalize
    from django.db.models import Count, Q, Sum # Ensure Sum is imported
    from django.core.cache import cache  # Add caching
    import logging # Add logging
    logger = logging.getLogger(__name__)
    
    # Cache configuration
    CACHE_TTL = 3600  # 1 hour cache
    
    # Generate cache key based on request parameters
    company_sort = request.GET.get('company_sort', 'count')
    company_order = request.GET.get('company_order', 'desc')
    tech_sort = request.GET.get('tech_sort', 'count')
    tech_order = request.GET.get('tech_order', 'desc')
    
    statistics_cache_key = f"statistics_{company_sort}_{company_order}_{tech_sort}_{tech_order}"
    
    # Try to get from cache first
    cached_context = cache.get(statistics_cache_key)
    if cached_context:
        logger.info(f"✅ Statistics cache HIT for key: {statistics_cache_key}")
        return render(request, 'checker/statistics.html', cached_context)
    
    logger.info(f"❌ Statistics cache MISS for key: {statistics_cache_key} - building data...")
    """

# Replace the import section
if import_section in content:
    content = content.replace(import_section, replacement)
    print("✅ Added cache check at beginning of function")
else:
    print("❌ Could not find import section to patch")
    
# Find the return statement and add caching before it
return_statement = "    return render(request, 'checker/statistics.html', context)"
cache_addition = """    # Cache the context before returning
    cache.set(statistics_cache_key, context, CACHE_TTL)
    logger.info(f"✅ Cached statistics data for key: {statistics_cache_key}")
    
    return render(request, 'checker/statistics.html', context)"""

if return_statement in content:
    content = content.replace(return_statement, cache_addition)
    print("✅ Added cache storage before return")
else:
    print("❌ Could not find return statement to patch")

# Write the patched content back
with open(views_file + '.patched', 'w') as f:
    f.write(content)

print("\n✅ Created patched file: checker/views.py.patched")
print("\nTo apply the patch:")
print("1. Backup current file: cp checker/views.py checker/views.py.backup")
print("2. Apply patch: cp checker/views.py.patched checker/views.py")
print("3. Restart server")
print("\nExpected improvements:")
print("  First load: ~1.2s (builds data)")
print("  Cached loads: <0.01s (instant!)")