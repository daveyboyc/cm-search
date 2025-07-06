# Redis Memory Optimization Guide

## Update May 2025
- **Company search has been removed from Redis** and converted to use LocationGroup model
- This significantly reduces Redis memory usage by ~1.6MB (company index)
- Search now uses PostgreSQL with GIN indexes instead of Redis caching

## Current Situation
- Redis usage should be significantly lower after removing company search
- Main Redis usage now:
  - Map tile caching (largest consumer)
  - Location-to-postcode mappings
  - CMU dataframe cache
- Need to keep costs low until monetization

## Immediate Actions

### 1. Reduce Map Cache TTL
In `checker/services/map_cache.py`, change:
```python
cache.set(cache_key, cache_data, timeout=60*60*24*7)  # 7 days
# TO:
cache.set(cache_key, cache_data, timeout=60*60*24*2)  # 2 days
```

### 2. Remove DSR from Map Cache
DSR has 28,270 components and takes 32s to cache. In `checker/views.py` or wherever map technologies are defined:
```python
# Exclude DSR from automatic caching
CACHED_TECHNOLOGIES = ['Gas', 'Wind', 'Solar', 'Battery', 'Nuclear', 'Biomass', 'Interconnector']
# Remove 'DSR' - generate it on-demand only
```

### 3. Add Cache Settings
In `capacity_checker/settings.py`:
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': redis_url,
        'TIMEOUT': 3600,  # 1 hour default
        'OPTIONS': {
            'MAX_ENTRIES': 5000,  # Limit total entries
            'CULL_FREQUENCY': 3,  # Remove 1/3 of entries when full
        }
    }
}
```

### 4. Monitor Usage
Run these commands periodically:
```bash
# Check memory usage
heroku redis:cli
> INFO memory
> DBSIZE

# Find large keys
> SCAN 0 COUNT 100
> MEMORY USAGE <key_name>

# Delete old search caches
> DEL search_cache:*
```

## Medium-term Solutions

### 1. Selective Caching Strategy
- Cache only top 5 technologies by usage
- Generate others on-demand
- Use shorter TTLs for less popular data

### 2. Data Compression
- Store map data as compressed JSON
- Use msgpack instead of JSON for smaller size

### 3. Split Redis Usage
- Use Heroku Redis for critical data (company index, CMU data)
- Use PostgreSQL cache table for map data
- Use session storage for user-specific data

## Long-term Options

### 1. If Monetizing via Subscriptions
- Upgrade to Redis Premium 0 ($15/month) when you have 5-10 paying users
- Gives you 100MB (2x current)

### 2. If Going Advertising Route
- Keep free tier
- Implement aggressive caching policies
- Use CDN for static map data
- Consider Cloudflare KV for edge caching

## Emergency Actions if Over Limit

```bash
# Clear all search caches
heroku redis:cli
> DEL search_cache:*

# Clear old map data
> SCAN 0 MATCH map_data:* COUNT 1000
> DEL <old_keys>

# Restart dynos to rebuild only essential caches
heroku restart
```

## Recommended Immediate Action
1. Remove DSR from automatic map caching
2. Reduce map cache TTL to 48 hours
3. Clear existing caches and let them rebuild with new settings

This should reduce memory usage by ~40-50% immediately.