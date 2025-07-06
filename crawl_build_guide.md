# CMR Database Update Process Guide

## Overview
The database update process involves 4 main phases, each with specific Redis memory and Supabase egress considerations.

## Current Status
- **Database CMUs**: 10,542
- **New CMUs to add**: 1,526
- **Estimated new components**: ~7,500 (based on average ratio)

## Phase 1: Data Crawling (`crawl_to_database.py`)

### What it does:
1. **Fetches CMU Registry data** from NESO API
   - Source: `https://api.neso.energy/api/3/action/datastore_search`
   - Resource ID: `25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6`
   - Processes 1,526 new CMU IDs

2. **For each CMU, fetches component details** from Component API
   - Resource ID: `790f5fa0-f8eb-4d82-b98d-0d34d3e404e8`
   - Average 5-10 components per CMU
   - **Total estimated API calls**: ~1,526 CMU calls + ~1,526 component calls = 3,052 calls

### Supabase Impact:
- **WRITES database directly** - This increases Supabase egress!
- **Estimated egress**: ~7,500 new components × 2KB each = **~15MB**
- **Duration**: 45-90 minutes (throttled to avoid rate limits)

### Redis Impact:
- **Minimal during crawl** - just checkpoint files
- **Risk**: None during this phase

### Command:
```bash
python manage.py crawl_to_database --resume --sleep 1.5
```

## Phase 2: Geocoding (`geocode_components.py`)

### What it does:
1. **Finds components without lat/lon coordinates**
2. **Uses external geocoding service** (Google/OpenStreetMap)
3. **Updates component records** with coordinates

### Supabase Impact:
- **WRITES coordinates back to database**
- **Estimated egress**: ~1,000 components × 0.5KB each = **~0.5MB**
- **Duration**: 30-60 minutes (rate limited by geocoding API)

### Redis Impact:
- **Minimal** - no cache building yet

### Command:
```bash
python manage.py geocode_components --limit 1000
```

## Phase 3: Search Index Rebuild (`rebuild_search_index.py`)

### What it does:
1. **Rebuilds PostgreSQL full-text search indexes**
2. **Updates search vectors** for all components
3. **Optimizes database indexes**

### Supabase Impact:
- **HIGH READ ACTIVITY** - reads all components to rebuild indexes
- **Estimated egress**: ~58,000 components × 1KB each = **~58MB**
- **Duration**: 15-30 minutes

### Redis Impact:
- **None** - pure database operation

### Command:
```bash
python manage.py rebuild_search_index
```

## Phase 4: Cache Rebuilding (Multiple Commands)

### 4a. Location Mapping (`build_location_mapping.py`)

**What it does:**
- Reads all component locations from database
- Builds location-to-postcode mapping
- Stores in Redis with NO expiration

**Supabase Impact:**
- **HIGH READ** - reads all 58,000+ components
- **Estimated egress**: ~58MB (reads all locations)

**Redis Impact:**
- **MAJOR MEMORY USAGE** - stores 15,000+ location mappings
- **Estimated size**: ~50-100MB
- **Risk**: 🚨 Could push Redis over 80% limit

### 4b. CMU Dataframe Cache (`cache_cmu.py`)

**What it does:**
- Reads all CMU registry data
- Builds pandas dataframe
- Caches in Redis (7-day expiration)

**Supabase Impact:**
- **Moderate read** - CMU registry only
- **Estimated egress**: ~15MB

**Redis Impact:**
- **Moderate memory** - ~20-30MB
- **Risk**: 🟡 Manageable

### 4c. Map Cache (`build_map_cache.py`)

**What it does:**
- Pre-generates map data for all technologies
- Creates clustered views for zoom levels 6-8
- Caches component coordinates and details

**Supabase Impact:**
- **MASSIVE READ** - reads components multiple times for different filters
- **Estimated egress**: ~200-400MB (multiple technology/zoom combinations)
- **Duration**: 20-40 minutes

**Redis Impact:**
- **MASSIVE MEMORY USAGE** - stores map data for 7 technologies × 2 zoom levels
- **Estimated size**: ~100-200MB
- **Risk**: 🚨 HIGH - likely to exceed Redis limits

### 4d. Company Index (`build_company_index.py`)

**What it does:**
- Groups components by company
- Builds search index
- Caches company statistics

**Supabase Impact:**
- **High read** - groups all components
- **Estimated egress**: ~58MB

**Redis Impact:**
- **Moderate memory** - ~10-20MB
- **Risk**: 🟡 Manageable

## Total Resource Estimation

### Supabase Egress (Shared Pool):
- **Phase 1 (Crawl)**: ~15MB
- **Phase 2 (Geocode)**: ~0.5MB
- **Phase 3 (Search Index)**: ~58MB
- **Phase 4a (Location Mapping)**: ~58MB
- **Phase 4b (CMU Cache)**: ~15MB
- **Phase 4c (Map Cache)**: ~300MB
- **Phase 4d (Company Index)**: ~58MB
- **TOTAL**: ~504MB egress

### Redis Memory:
- **Current usage**: ~50-60% (estimated)
- **Location mapping**: +50-100MB
- **Map cache**: +100-200MB
- **Other caches**: +50MB
- **TOTAL INCREASE**: +200-350MB
- **Risk**: 🚨 **VERY HIGH** - likely to exceed 80% limit

## Recommended Monitoring Strategy

### Before Starting:
```bash
# Check current Redis usage
python emergency_redis_cleanup.py --check-only

# Check current Supabase usage for the day
# (Manual check in Supabase dashboard)
```

### During Process:
```bash
# Monitor Redis every 10 minutes
watch -n 600 "python emergency_redis_cleanup.py --check-only"

# Run between phases if memory > 70%
python emergency_redis_cleanup.py
```

### Redis Emergency Cleanup:
- Removes old/duplicate caches
- Shortens TTLs on non-critical data
- Clears map cache if needed (regenerates on-demand)

## Recommended Phased Approach

### Option 1: Full Update (High Risk)
Run all phases sequentially with monitoring.

### Option 2: Incremental Update (Safer)
1. **Week 1**: Crawl + Geocode only
2. **Week 2**: Search index rebuild
3. **Week 3**: Core caches (location, CMU, company)
4. **Week 4**: Map cache (if Redis has space)

### Option 3: Selective Update
- Skip map cache rebuild (it regenerates on-demand)
- Focus on data integrity (crawl + geocode + search index)

## Emergency Mitigation

If Redis hits 80%+ during process:
1. **Stop current operation**
2. **Run emergency cleanup**
3. **Disable map cache generation**
4. **Continue with core operations only**

## Commands Summary

```bash
# 1. Data crawl (45-90 min)
python manage.py crawl_to_database --resume --sleep 1.5

# 2. Geocoding (30-60 min)  
python manage.py geocode_components --limit 1000

# 3. Search index (15-30 min)
python manage.py rebuild_search_index

# 4. Core caches only (safer)
python manage.py build_location_mapping
python manage.py cache_cmu
python manage.py build_company_index

# 5. Map cache (only if Redis has space)
python manage.py build_map_cache
```

Ready to proceed with monitoring strategy in place?