# Redis Optimization Guide

## Problem Summary

Redis usage was spiking to 98% before dropping to 80% due to:

1. **Large cached data structures**:
   - CMU dataframe (~15MB with pickle+base64 encoding overhead)
   - Map cache data (especially DSR technology with 28,270 components)
   - Statistics aggregations cached for long periods

2. **Frequent dyno restarts** (~50/day on Heroku) causing repeated cache loading during startup validation

3. **Long TTLs** (2-7 days) preventing natural cache expiration

4. **No memory limits or eviction policies** in Redis configuration

## Root Causes Analysis

### 1. Startup Cache Loading (`checker/apps.py`)
- On every app startup, validates and potentially loads:
  - CMU dataframe
  - Company index
  - Map cache
  - Location mappings
- With ~50 dyno restarts/day, this creates significant Redis traffic

### 2. Map Cache (`checker/services/map_cache.py`)
- Caches map data for 2 days (was 7 days)
- DSR technology alone has 28,270 components
- Multiple zoom levels and viewports cached
- No size limits on cached data

### 3. CMU Dataframe (`checker/services/data_access.py`)
- Serialized with pickle + base64 (83% overhead)
- Cached for 7 days
- ~15MB per cache entry

### 4. Missing Redis Configuration
- No `MAX_ENTRIES` limit
- No `CULL_FREQUENCY` for automatic cleanup
- No eviction policy configured

## Solution Implementation

### Step 1: Run Analysis Script

```bash
# Analyze current Redis usage and optionally clear large caches
python fix_redis_spikes.py
```

This script will:
- Show current Redis memory usage
- Analyze cache entry sizes
- Optionally clear large cache entries
- Provide recommendations

### Step 2: Reduce Cache TTLs

```bash
# Update cache TTLs across the codebase
python reduce_cache_ttls.py
```

This reduces:
- Map cache: 2 days → 1 day
- CMU dataframe: 7 days → 1 day  
- Statistics: 6 hours → 1 hour
- Search results: 1 hour → 30 minutes

### Step 3: Update Redis Configuration

```bash
# Patch Django settings with memory management
python patch_redis_settings.py
```

Adds:
- Connection pool settings
- Compression support
- Exception handling
- Monitoring settings

### Step 4: Enable Emergency Mode

```bash
# Set emergency environment variables on Heroku
heroku config:set REDIS_EMERGENCY_MODE=true DISABLE_MAP_CACHE=true -a your-app-name
```

This will:
- Skip startup cache validation (reduces dyno restart load)
- Disable map caching temporarily
- Significantly reduce Redis traffic

### Step 5: Deploy Changes

```bash
# Commit all changes
git add -A
git commit -m "Fix Redis memory spikes with reduced TTLs and emergency mode"

# Deploy to Heroku
git push heroku help-guide-improvements:main
```

### Step 6: Monitor Redis Usage

```bash
# Check Redis memory usage
heroku redis:info -a your-app-name

# View Redis metrics in dashboard
heroku redis:cli -a your-app-name
> INFO memory
> CONFIG GET maxmemory
```

## Gradual Recovery Process

Once Redis usage stabilizes below 80%:

### 1. Re-enable Map Caching (Week 1)
```bash
heroku config:unset DISABLE_MAP_CACHE -a your-app-name
```

### 2. Re-enable Startup Validation (Week 2)
```bash
heroku config:unset REDIS_EMERGENCY_MODE -a your-app-name
```

### 3. Monitor and Adjust TTLs (Week 3+)
If usage remains stable, gradually increase TTLs:
- Map cache: 1 day → 2 days
- CMU dataframe: 1 day → 3 days

## Long-term Solutions

### 1. Move Static Data to Files
- Location mappings (already done - saved 71.5GB)
- Consider moving CMU dataframe to static JSON
- Pre-generate common map views as static files

### 2. Implement Smart Caching
```python
# Only cache popular items
if component_count < 1000:  # Only cache smaller datasets
    cache.set(cache_key, data, timeout=3600)

# Check memory before caching
if get_redis_memory_percent() < 80:
    cache.set(cache_key, large_data, timeout=3600)
```

### 3. Use Compression
```python
import msgpack
import zlib

# Compress before caching
compressed = zlib.compress(msgpack.packb(data))
cache.set(key, compressed, timeout=3600)

# Decompress when retrieving
compressed = cache.get(key)
data = msgpack.unpackb(zlib.decompress(compressed))
```

### 4. Add Redis Monitoring
```python
# Add to views or middleware
def check_redis_health():
    memory_percent = get_redis_memory_percent()
    if memory_percent > 90:
        logger.warning(f"Redis memory critical: {memory_percent}%")
        # Trigger cache cleanup
        clear_old_cache_entries()
```

### 5. Consider Alternative Caching Strategies

#### For Large Static Data:
- Use CDN (CloudFlare, Fastly)
- Static file generation
- Edge caching

#### For Dynamic Data:
- PostgreSQL cache table (free with Heroku)
- Local memory cache (per-dyno)
- Implement cache warming during off-peak

## Monitoring Commands

```bash
# Real-time Redis monitoring
heroku redis:cli -a your-app-name
> MONITOR  # Watch commands in real-time (careful - high overhead)

# Memory analysis
> MEMORY STATS
> MEMORY DOCTOR

# Key analysis
> DBSIZE  # Total number of keys
> SCAN 0 COUNT 100  # Sample keys
> MEMORY USAGE <key>  # Size of specific key

# Find large keys
> redis-cli --bigkeys

# Set memory limit (if not set)
> CONFIG SET maxmemory 5gb
> CONFIG SET maxmemory-policy allkeys-lru
```

## Emergency Cache Clear

If Redis hits 100% and the app becomes unresponsive:

```bash
# Option 1: Clear all cache via Heroku CLI
heroku redis:cli -a your-app-name
> FLUSHDB

# Option 2: Clear via Django
heroku run python manage.py shell -a your-app-name
>>> from django.core.cache import cache
>>> cache.clear()

# Option 3: Clear specific patterns
heroku run python -a your-app-name << EOF
from django.core.cache import cache
import redis
r = redis.from_url(cache._cache.connection_pool.connection_kwargs['url'])
for key in r.scan_iter("map_*"):
    r.delete(key)
EOF
```

## Prevention Checklist

- [ ] Set reasonable TTLs (minutes/hours, not days)
- [ ] Implement size checks before caching large data
- [ ] Use compression for large objects
- [ ] Monitor Redis memory percentage
- [ ] Set up alerts for >80% usage
- [ ] Implement cache warming during low-traffic periods
- [ ] Use static files for unchanging data
- [ ] Consider CDN for geographic data
- [ ] Implement graceful degradation when cache is unavailable
- [ ] Regular cache key cleanup (remove unused patterns)

## Key Metrics to Track

1. **Redis Memory Usage**: Should stay below 80%
2. **Cache Hit Rate**: Should be >70% for effective caching
3. **Average Key Size**: Identify unusually large entries
4. **Eviction Rate**: High evictions indicate memory pressure
5. **Connection Count**: High connections may indicate connection leak

## References

- [Redis Memory Optimization](https://redis.io/docs/manual/memory-optimization/)
- [Django Cache Framework](https://docs.djangoproject.com/en/4.2/topics/cache/)
- [Heroku Redis Documentation](https://devcenter.heroku.com/articles/heroku-redis)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)