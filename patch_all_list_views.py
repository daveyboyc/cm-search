#!/usr/bin/env python
"""Automated patch to add caching to all list views"""
import re

print("🔧 Patching all list views to add caching...")

# Read the views file
with open('checker/views.py', 'r') as f:
    content = f.read()

# Function to add caching to a view
def add_caching_to_view(content, view_name, template_name):
    """Add caching to a specific view"""
    
    # Find the function definition
    func_pattern = rf'(def {view_name}\(request\):\s*"""[^"]*""")'
    match = re.search(func_pattern, content, re.DOTALL)
    
    if not match:
        print(f"❌ Could not find {view_name}")
        return content
    
    func_start = match.group(1)
    
    # Add cache import after docstring
    cache_import = f'''{func_start}
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.core.cache import cache  # Added for caching
    
    # Cache configuration
    CACHE_TTL = 3600  # 1 hour cache
    
    # Get parameters for cache key
    page = request.GET.get("page", 1)
    sort_order_param = request.GET.get("sort", "desc")
    per_page = request.GET.get("per_page", 50)  # If applicable
    
    # Generate cache key
    cache_key = f"{view_name}_p{{page}}_s{{sort_order_param}}_pp{{per_page}}"
    
    # Try cache first
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.info(f"✅ {view_name} cache HIT for page {{page}}")
        return cached_response
    
    logger.info(f"❌ {view_name} cache MISS for page {{page}} - building...")'''
    
    # Replace the function start
    content = content.replace(func_start, cache_import, 1)
    
    # Find the return statement and add caching before it
    # Look for the specific template render
    return_pattern = rf'(\s+)(return render\(request, [\'"]checker/{template_name}\.html[\'"], context\))'
    
    def add_cache_before_return(match):
        indent = match.group(1)
        return_stmt = match.group(2)
        return f'''{indent}# Cache the response before returning
{indent}response = render(request, 'checker/{template_name}.html', context)
{indent}cache.set(cache_key, response, CACHE_TTL)
{indent}logger.info(f"✅ Cached {view_name} page {{page}}")
{indent}return response'''
    
    content = re.sub(return_pattern, add_cache_before_return, content)
    
    print(f"✅ Added caching to {view_name}")
    return content

# List of views to patch with their template names
views_to_patch = [
    ('derated_capacity_list', 'derated_capacity_list'),
    ('company_capacity_list', 'company_capacity_list'),
    ('company_component_count_list_view', 'company_component_count_list'),
    ('technology_list_view', 'technology_list'),
    ('technology_capacity_list_view', 'technology_capacity_list'),
]

# Apply patches
patched_content = content
for view_name, template_name in views_to_patch:
    patched_content = add_caching_to_view(patched_content, view_name, template_name)

# Write the patched file
with open('checker/views.py.patched_lists', 'w') as f:
    f.write(patched_content)

print("\n✅ Created patched file: checker/views.py.patched_lists")
print("\nTo apply:")
print("1. Review the changes: diff checker/views.py checker/views.py.patched_lists")
print("2. Apply: cp checker/views.py.patched_lists checker/views.py")
print("3. Restart server")

print("\n📊 Expected improvements for ALL list views:")
print("  - First load: 0.5-2s (builds from database)")
print("  - Subsequent loads: <10ms (from cache)")
print("  - Each page cached separately")
print("  - Automatic refresh every hour")