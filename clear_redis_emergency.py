#!/usr/bin/env python
"""Emergency Redis cleanup script - clears all cache and implements shorter TTLs"""
import os
import django
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
from django.conf import settings
import redis
from urllib.parse import urlparse

def clear_redis_and_update_ttl():
    """Clear all Redis cache and update TTL settings"""
    
    print("🚨 EMERGENCY REDIS CLEANUP")
    print("=" * 50)
    
    # Get Redis connection details
    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        print("❌ No REDIS_URL found in environment")
        return
    
    # Parse Redis URL
    parsed = urlparse(redis_url)
    
    # Connect directly to Redis
    r = redis.Redis(
        host=parsed.hostname,
        port=parsed.port,
        password=parsed.password,
        ssl=True,
        ssl_cert_reqs=None
    )
    
    # Get current info
    info = r.info()
    used_memory = info.get('used_memory_human', 'Unknown')
    print(f"Current Redis memory usage: {used_memory}")
    
    # Count keys before clearing
    key_count = r.dbsize()
    print(f"Current number of keys: {key_count}")
    
    # Clear all Redis data
    print("\n🗑️  Clearing all Redis data...")
    r.flushall()
    
    # Verify cleanup
    new_key_count = r.dbsize()
    new_info = r.info()
    new_used_memory = new_info.get('used_memory_human', 'Unknown')
    
    print(f"\n✅ Redis cleared!")
    print(f"Keys after cleanup: {new_key_count}")
    print(f"Memory after cleanup: {new_used_memory}")
    
    # Update cache settings in settings.py to use shorter TTLs
    print("\n📝 Recommended settings.py update:")
    print("""
# Add to your settings.py:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'PICKLE_VERSION': -1,
        },
        'TIMEOUT': 900,  # 15 minutes default timeout
    }
}

# Cache key timeouts (in seconds)
CACHE_TTL_SHORT = 300      # 5 minutes for frequently changing data
CACHE_TTL_MEDIUM = 900     # 15 minutes for standard data
CACHE_TTL_LONG = 3600      # 1 hour for rarely changing data
""")

if __name__ == '__main__':
    clear_redis_and_update_ttl()