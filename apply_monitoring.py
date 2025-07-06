"""
Script to apply monitoring to existing views and APIs
"""
import os
import re

def apply_monitoring_to_views():
    """Apply monitoring decorators to existing API views"""
    
    # Map view endpoints
    map_api_file = 'checker/views.py'
    search_geojson_file = 'checker/views_search_geojson.py'
    map_results_file = 'checker/views_map_results.py'
    
    # Apply monitoring to map data API
    apply_decorator_to_function(
        map_api_file, 
        'map_data_api',
        '@monitor_map_api'
    )
    
    # Apply monitoring to search GeoJSON API  
    apply_decorator_to_function(
        search_geojson_file,
        'search_results_geojson', 
        '@monitor_search_api'
    )
    
    # Apply monitoring to component detail API
    apply_decorator_to_function(
        map_api_file,
        'component_map_detail_api',
        '@monitor_component_detail'
    )
    
    # Apply monitoring to map results view
    apply_decorator_to_function(
        map_results_file,
        'map_search_results_view',
        '@monitor_api_endpoint("/map_results/")'
    )
    
    print("✅ Applied monitoring decorators to API views")


def apply_decorator_to_function(file_path, function_name, decorator):
    """Add decorator to a specific function in a file"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the function definition
    pattern = rf'^def {function_name}\('
    match = re.search(pattern, content, re.MULTILINE)
    
    if not match:
        print(f"❌ Function {function_name} not found in {file_path}")
        return
    
    # Check if decorator already exists
    lines = content.split('\n')
    function_line_num = content[:match.start()].count('\n')
    
    # Look backwards from function definition to see if decorator already exists
    has_decorator = False
    for i in range(max(0, function_line_num - 5), function_line_num):
        if decorator.split('(')[0] in lines[i]:  # Check decorator name without params
            has_decorator = True
            break
    
    if has_decorator:
        print(f"⚠️  Decorator already exists for {function_name} in {file_path}")
        return
    
    # Add import for monitoring decorators at top of file
    import_line = "from monitoring.decorators import monitor_api_endpoint, monitor_map_api, monitor_search_api, monitor_component_detail"
    if import_line not in content:
        # Find a good place to add the import
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                import_index = i + 1
        
        lines.insert(import_index, import_line)
        content = '\n'.join(lines)
    
    # Add decorator before function
    lines = content.split('\n')
    function_line_num = content.count('\n', 0, content.find(f'def {function_name}('))
    lines.insert(function_line_num, decorator)
    
    # Write back to file
    with open(file_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Added {decorator} to {function_name} in {file_path}")


def add_middleware_to_settings():
    """Add monitoring middleware to Django settings"""
    settings_file = 'capacity_checker/settings.py'
    
    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        return
    
    with open(settings_file, 'r') as f:
        content = f.read()
    
    # Check if middleware already added
    if 'monitoring.middleware' in content:
        print("⚠️  Monitoring middleware already in settings")
        return
    
    # Find MIDDLEWARE setting
    middleware_pattern = r'MIDDLEWARE = \[(.*?)\]'
    match = re.search(middleware_pattern, content, re.DOTALL)
    
    if not match:
        print("❌ MIDDLEWARE setting not found in settings.py")
        return
    
    # Add monitoring middleware
    middleware_items = match.group(1).strip().split('\n')
    middleware_items.insert(1, "    'monitoring.middleware.EgressMonitoringMiddleware',")
    middleware_items.insert(2, "    'monitoring.middleware.DatabaseQueryMonitoringMiddleware',")
    
    new_middleware = 'MIDDLEWARE = [\n' + '\n'.join(middleware_items) + '\n]'
    
    content = content.replace(match.group(0), new_middleware)
    
    with open(settings_file, 'w') as f:
        f.write(content)
    
    print("✅ Added monitoring middleware to settings")


def add_monitoring_urls():
    """Add monitoring URLs to main URLconf"""
    urls_file = 'capacity_checker/urls.py'
    
    if not os.path.exists(urls_file):
        print(f"❌ URLs file not found: {urls_file}")
        return
    
    with open(urls_file, 'r') as f:
        content = f.read()
    
    # Check if monitoring URLs already added
    if 'monitoring/' in content:
        print("⚠️  Monitoring URLs already added")
        return
    
    # Add monitoring URL include
    if "path('monitoring/', include('monitoring.urls'))," not in content:
        # Find urlpatterns
        pattern = r'urlpatterns = \[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            url_items = match.group(1).strip().split('\n')
            url_items.insert(1, "    path('monitoring/', include('monitoring.urls')),")
            
            new_urlpatterns = 'urlpatterns = [\n' + '\n'.join(url_items) + '\n]'
            content = content.replace(match.group(0), new_urlpatterns)
            
            # Add include import if needed
            if 'from django.urls import include' not in content:
                content = content.replace(
                    'from django.urls import path',
                    'from django.urls import path, include'
                )
    
    with open(urls_file, 'w') as f:
        f.write(content)
    
    print("✅ Added monitoring URLs to main URLconf")


def create_monitoring_startup():
    """Create script to start monitoring daemon"""
    startup_script = """
# Add this to your Django app's ready() method or manage.py

from monitoring.egress_monitor import start_monitoring_daemon

# Start the monitoring daemon
start_monitoring_daemon()
print("🚀 Egress monitoring daemon started")
"""
    
    with open('start_monitoring.py', 'w') as f:
        f.write(startup_script.strip())
    
    print("✅ Created start_monitoring.py script")


if __name__ == '__main__':
    print("🚀 Applying comprehensive egress monitoring...")
    
    # Apply all monitoring components
    apply_monitoring_to_views()
    add_middleware_to_settings()
    add_monitoring_urls()
    create_monitoring_startup()
    
    print("\n" + "="*50)
    print("✅ MONITORING SETUP COMPLETE!")
    print("="*50)
    print("\nNext steps:")
    print("1. Run: python manage.py migrate")
    print("2. Add 'monitoring' to INSTALLED_APPS in settings.py")
    print("3. Visit: http://localhost:8000/monitoring/ for dashboard")
    print("4. Import and run: from monitoring.egress_monitor import start_monitoring_daemon; start_monitoring_daemon()")
    print("\nThe monitoring will track:")
    print("- 📊 All API calls and response sizes")
    print("- 🗄️  Database queries and data transfer")
    print("- 💾 Redis commands and cache performance")
    print("- 🖥️  System resources (CPU, memory, network)")
    print("- ⚠️  Automatic alerts for large responses")
    print("- 📈 Real-time dashboard with monthly estimates")