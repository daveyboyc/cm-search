# Redis and Cache Usage After Optimizations

## 🔴 What We're Still Using Redis For:

### 1. **Django Cache Backend**
- All the new view caching (statistics, list views)
- Search result caching
- Component detail caching
- Session storage

### 2. **Pre-built Indexes** (Still in Redis)
- CMU dataframe (~15MB)
- Company index (~5MB)
- Map data cache
- Search result caching

### 3. **What We REMOVED from Redis**
- Location mappings (was 71.5GB, now 3MB static files)
- Postcode lookups (now instant from static files)

## 📊 Redis Usage Impact:
- **Before**: 71.5GB (1429% over 5GB limit)
- **After**: <5GB estimated
- **Reduction**: ~93%

## 🌐 Supabase Egress Impact:
- **Dramatically reduced** database queries:
  - Location searches: No longer hit database
  - Statistics page: Cached for 1 hour (was hitting DB every load)
  - List views: All cached for 1 hour
  - Search results: Cached for faster repeat searches
  
- **Estimated reduction**: 70-90% fewer database queries

## 💡 Alternative Cache Backends:

### Option 1: Use Heroku's Free PostgreSQL for Cache
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}
```

### Option 2: Use File-Based Cache (Free)
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache',
    }
}
```

### Option 3: Upstash Redis (10,000 commands/day free)
- Good for light caching
- Won't work for heavy CMU dataframe storage

### Option 4: Memory Cache (per-dyno)
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

## 🚀 Recommendation:
1. Keep Redis for now (should be under 5GB)
2. Monitor actual usage after deployment
3. If still over limit, move CMU dataframe to static files
4. Consider PostgreSQL cache table as free alternative