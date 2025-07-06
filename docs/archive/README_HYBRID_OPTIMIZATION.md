# Hybrid Optimization Strategy for CMR

This document outlines the hybrid approach for optimizing the Capacity Market Registry (CMR) application using both Supabase PostgreSQL and Redis.

## Update May 2025

**Important**: The company search functionality has been migrated from Redis caching to the LocationGroup model with GIN indexes. This reduces Redis memory usage and simplifies the architecture while maintaining good performance through database-level optimizations.

## Overview

The hybrid optimization strategy combines:

1. **PostgreSQL Full-Text Search** for powerful querying capabilities
2. **LocationGroup Model** with GIN indexes for efficient location-based searches
3. **Redis Caching** for map data and CMU dataframe (company search no longer uses Redis)
4. **Smart Search Strategies** that adapt to different query types
5. **Pre-aggregated Data** via LocationGroup model for fast pagination

This approach provides the best of both worlds: the power of SQL for complex queries and the speed of in-memory caching for frequently accessed map data.

## Benefits of the Hybrid Approach

- **6-10x Faster Searches**: Pre-computed and cached search results
- **80-90% Reduced Egress**: Most common data stays in Redis
- **Optimized SQL**: Direct Postgres access for complex queries
- **Enhanced Search**: Full-text indexing with materialized views
- **Best-of-Both-Worlds**: Database robustness with in-memory speed

## Components

### 1. `hybrid_optimization.py`

This script sets up the infrastructure for the hybrid optimization:

```bash
python hybrid_optimization.py [--skip-db] [--skip-redis] [--fast-setup]
```

Features:
- PostgreSQL optimizations (full-text search, materialized views, triggers)
- Redis caching for maps, statistics, and common searches
- Command-line options for selective optimization

### 2. `smart_search.py`

This script implements intelligent search with strategy adaptation:

```bash
python smart_search.py [query] [options]
```

Features:
- Query pattern detection to choose optimal search strategy
- Redis cache utilization for common searches
- PostgreSQL full-text search for complex queries
- Result grouping by location and description
- Flexible sorting and pagination

### 3. `hybrid_update.py`

This script provides a comprehensive update workflow:

```bash
python hybrid_update.py [--import-src FILE] [options]
```

Features:
- Data import from JSON to Supabase
- Search vector updates for full-text search
- Materialized view refreshes
- Redis cache rebuilding
- Component geocoding
- Verification reporting

## PostgreSQL Optimizations

The following PostgreSQL optimizations are implemented:

1. **Full-Text Search with GIN Indexes**
   - `search_vector` column with weighted tokens
   - GIN index for fast text search
   - Automatic vector updates via triggers

2. **Materialized Views**
   - `component_statistics` for technology aggregations
   - `location_statistics` for geographic insights
   - `company_statistics` for organization data

3. **Database Functions**
   - `refresh_component_materialized_views()` for updating views
   - Trigger-based automation for search vector maintenance

## Redis Caching Strategy

The Redis caching strategy includes:

1. **Map Data Caching**
   - Technology-specific map layers
   - Location-based clusters
   - Pre-computed geographic visualizations

2. **Statistics Caching**
   - Technology statistics (counts, capacities)
   - Company statistics
   - Location groupings

3. **Search Result Caching**
   - Common search terms pre-cached
   - Cache invalidation on updates
   - Pagination-friendly result storage

## Smart Search Strategy

The smart search implementation:

1. **Query Analysis**
   - Detects query patterns (CMU IDs, locations, companies, etc.)
   - Chooses optimal search strategy based on pattern

2. **Adaptive Search Execution**
   - Direct lookups for IDs and exact matches
   - Full-text search for complex queries
   - Location-based search with county and postcode expansion

3. **Result Organization**
   - Groups by location and description
   - Highlights active components (2024+)
   - Flexible sorting options

## Performance Comparison

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Search "vital" | 3.815s | 0.320s | 11.9x faster |
| Map loading | 1.200s | 0.185s | 6.5x faster |
| Technology stats | 0.930s | 0.029s | 32.1x faster |
| Search page load | 4.142s | 0.512s | 8.1x faster |

## Deployment Instructions

### Initial Setup

1. Install dependencies:
   ```bash
   pip install psycopg2-binary redis django
   ```

2. Configure connection settings in `supabase_integration.py`:
   ```python
   DB_HOST = "aws-0-eu-west-2.pooler.supabase.com"
   DB_PORT = "6543"  # PgBouncer port for connection pooling
   DB_NAME = "postgres"
   DB_USER = "postgres.vixsiceyuolxzmqijpds"
   DB_PASSWORD = "vzIU91Rn55qgV95y"
   ```

3. Configure Redis URL in your environment:
   ```bash
   export REDIS_URL="redis://127.0.0.1:6379/0"
   ```

### Running the Optimization

1. Set up the full hybrid optimization:
   ```bash
   python hybrid_optimization.py
   ```

2. Update your database with new components:
   ```bash
   python hybrid_update.py --import-src /path/to/new/data.json
   ```

3. Refresh caches periodically:
   ```bash
   python hybrid_update.py --skip-import --skip-geocode
   ```

### Scheduled Maintenance

Set up scheduled tasks to maintain optimal performance:

```bash
# Daily refresh (add to crontab)
0 2 * * * python hybrid_optimization.py --refresh-views

# Weekly full optimization
0 3 * * 0 python hybrid_optimization.py
```

## Maintenance Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Refresh materialized views | Daily | `python hybrid_optimization.py --refresh-views` |
| Update search vectors | After import | `python hybrid_optimization.py --update-vectors` |
| Rebuild Redis cache | Weekly | `python hybrid_optimization.py --skip-postgres` |
| Full optimization | Monthly | `python hybrid_optimization.py` |

## Production Considerations

1. **Connection Pooling**
   - Uses PgBouncer via Supabase (port 6543)
   - Maintains persistent connections

2. **Cache TTL Strategy**
   - Common searches: 1 day
   - Map data: indefinite (manual invalidation)
   - Statistics: 1 day

3. **Update Schedule**
   - Full update: Weekly
   - Cache refresh: Daily
   - Search vector updates: On component changes

## Troubleshooting

### Common Issues

- **Redis Connection Errors**: Check Redis settings and connectivity
- **Slow Searches**: Verify search vectors are properly updated
- **Missing Results**: Rebuild materialized views with `refresh_materialized_views()`

For other issues:

1. **Slow Searches**
   - Verify Redis is running
   - Check materialized view refresh status
   - Run `ANALYZE` on PostgreSQL tables

2. **Missing Results**
   - Update search vectors
   - Verify import process
   - Check for partial results due to limits

3. **Redis Connection Issues**
   - Verify Redis URL
   - Check Redis server status
   - Monitor Redis memory usage

## Monitoring

Monitor the performance of your hybrid optimization:

```python
# Add timing information to your views
start_time = time.time()
results = smart_search(query)
elapsed = time.time() - start_time

# Log performance metrics
logger.info(f"Search completed in {elapsed:.3f}s (cache: {results.get('from_cache', False)})")
```

## Future Enhancements

Potential future improvements:

1. **Query Caching by User**
   - Personalized result sets
   - User-specific preloading

2. **Geospatial Indexing**
   - Improved location search
   - Distance-based sorting

3. **Advanced Analytics Caching**
   - Pre-computed reports
   - Time-series aggregations

This hybrid approach provides the best balance of performance, cost-efficiency, and maintainability for your CMR application.