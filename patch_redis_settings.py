#!/usr/bin/env python
"""
Patch Django settings to add Redis memory management options.
"""
import os
import re

def patch_settings():
    settings_path = "capacity_checker/settings.py"
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # Find the CACHES configuration
    cache_pattern = r"CACHES = \{[^}]+\{[^}]+\}[^}]+\}"
    
    # New cache configuration with memory management
    new_cache_config = """CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': redis_url,
        'TIMEOUT': 3600,  # 1 hour default timeout
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            # Memory management options
            'COMPRESSOR': 'django.core.cache.backends.redis.ZlibCompressor',  # Enable compression
            'IGNORE_EXCEPTIONS': True,  # Continue if Redis is down
        }
    }
}"""
    
    # Replace the CACHES configuration
    new_content = re.sub(cache_pattern, new_cache_config, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(settings_path, 'w') as f:
            f.write(new_content)
        print(f"✅ Updated {settings_path} with Redis memory management options")
    else:
        print(f"❌ Could not find CACHES configuration in {settings_path}")
        
    # Also add cache size monitoring settings
    monitoring_settings = """
# Redis monitoring and limits
REDIS_MAX_MEMORY_PERCENT = 80  # Warn when Redis uses more than 80% memory
CACHE_MIDDLEWARE_SECONDS = 600  # Cache pages for 10 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'cmr'
"""
    
    if "REDIS_MAX_MEMORY_PERCENT" not in content:
        with open(settings_path, 'a') as f:
            f.write(monitoring_settings)
        print("✅ Added Redis monitoring settings")

if __name__ == "__main__":
    patch_settings()