"""
Smart cache management for Redis memory optimization
Monitors Redis memory usage and clears cache when approaching limits
"""
import redis
import logging
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.cache import cache_page
from functools import wraps

logger = logging.getLogger(__name__)

class SmartCacheManager:
    """Manages Redis cache with memory monitoring"""
    
    def __init__(self):
        self.redis_url = settings.CACHES['default']['LOCATION']
        self.threshold = 0.7  # Clear cache at 70% memory usage
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(self.redis_url)
            logger.info("Smart cache manager initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
    
    def check_memory_usage(self):
        """Check Redis memory usage percentage"""
        if not self.redis_client:
            return 0.0
        
        try:
            info = self.redis_client.info('memory')
            used_memory = info.get('used_memory', 0)
            
            # Heroku Redis free tier is 30MB
            max_memory = 30 * 1024 * 1024  # 30MB in bytes
            
            usage_percentage = used_memory / max_memory
            logger.debug(f"Redis memory usage: {usage_percentage:.1%} ({used_memory / 1024 / 1024:.1f}MB / 30MB)")
            return usage_percentage
        except Exception as e:
            logger.error(f"Error checking Redis memory: {e}")
            return 0.0
    
    def clear_cache_if_needed(self):
        """Clear cache if memory usage exceeds threshold"""
        usage = self.check_memory_usage()
        
        if usage >= self.threshold:
            logger.warning(f"Redis memory usage at {usage:.1%}, clearing cache...")
            try:
                cache.clear()
                logger.info("Cache cleared successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
        return False

# Global instance
smart_cache_manager = SmartCacheManager()

def smart_cache(timeout):
    """
    Smart cache decorator that monitors memory usage
    and clears cache when approaching limits
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check and clear cache if needed before caching
            smart_cache_manager.clear_cache_if_needed()
            
            # Apply standard cache_page decorator
            cached_view = cache_page(timeout)(view_func)
            return cached_view(request, *args, **kwargs)
        return wrapper
    return decorator

# Convenience decorators with appropriate timeouts
short_cache = smart_cache(120)  # 2 minutes
medium_cache = smart_cache(300)  # 5 minutes  
long_cache = smart_cache(600)  # 10 minutes