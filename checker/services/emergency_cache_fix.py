"""
Emergency cache configuration to reduce Redis network usage
"""
import os
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# Emergency flags
DISABLE_MAP_CACHE = os.environ.get('DISABLE_MAP_CACHE', 'true').lower() == 'true'
DISABLE_SEARCH_CACHE = os.environ.get('DISABLE_SEARCH_CACHE', 'true').lower() == 'true'
USE_MINIMAL_CACHE = os.environ.get('USE_MINIMAL_CACHE', 'true').lower() == 'true'

# In-memory storage for critical data (per worker)
_memory_store = {
    'company_index': None,
    'company_index_time': 0,
    'cmu_df': None,
    'cmu_df_time': 0,
    'location_mapping': None,
    'location_mapping_time': 0
}

def should_use_redis(cache_type):
    """Determine if we should use Redis for this cache type"""
    if USE_MINIMAL_CACHE:
        # Only use Redis for absolute essentials
        essential_caches = ['session', 'csrf']
        return cache_type in essential_caches
    
    if cache_type == 'map' and DISABLE_MAP_CACHE:
        return False
    
    if cache_type == 'search' and DISABLE_SEARCH_CACHE:
        return False
    
    return True

def get_from_cache(key, cache_type='general'):
    """Wrapper around cache.get that respects emergency settings"""
    if not should_use_redis(cache_type):
        logger.debug(f"Skipping Redis for {cache_type}: {key}")
        return None
    
    try:
        return cache.get(key)
    except Exception as e:
        logger.error(f"Redis error (network limit?): {e}")
        return None

def set_to_cache(key, value, timeout=3600, cache_type='general'):
    """Wrapper around cache.set that respects emergency settings"""
    if not should_use_redis(cache_type):
        logger.debug(f"Skipping Redis set for {cache_type}: {key}")
        return False
    
    try:
        return cache.set(key, value, timeout)
    except Exception as e:
        logger.error(f"Redis set error (network limit?): {e}")
        return False

def get_with_memory_fallback(key, data_type, builder_func=None):
    """Try memory first, then Redis, then build from scratch"""
    import time
    
    # Check in-memory store first
    memory_key = data_type
    if memory_key in _memory_store:
        data = _memory_store[memory_key]
        timestamp = _memory_store.get(f"{memory_key}_time", 0)
        
        # Use memory cache if less than 1 hour old
        if data is not None and (time.time() - timestamp) < 3600:
            logger.info(f"Using in-memory cache for {data_type}")
            return data
    
    # Try Redis if allowed
    if should_use_redis(data_type):
        try:
            data = cache.get(key)
            if data:
                # Store in memory for next time
                _memory_store[memory_key] = data
                _memory_store[f"{memory_key}_time"] = time.time()
                return data
        except Exception as e:
            logger.error(f"Redis failed for {key}: {e}")
    
    # Build from scratch if we have a builder
    if builder_func:
        logger.warning(f"Building {data_type} from scratch")
        data = builder_func()
        if data:
            # Store in memory only
            _memory_store[memory_key] = data
            _memory_store[f"{memory_key}_time"] = time.time()
        return data
    
    return None