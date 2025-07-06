# CMR Local Optimization Guide

This guide explains how to use the optimized local scripts to improve your CMR application's performance without requiring Supabase.

## Overview

The optimized local scripts eliminate redundancy in the update process and improve performance by:

1. Consolidating multiple management commands into a single workflow
2. Leveraging PostgreSQL full-text search for faster queries
3. Building optimized caches for frequently accessed data
4. Using proper indexing for better database performance

## Quick Start

### One-Time Setup

Run the PostgreSQL search setup script to enable full-text search capabilities:

```bash
python setup_postgresql_search.py
```

### Regular Database Updates

Use the consolidated update script for your routine updates:

```bash
python update_database.py
```

This replaces multiple separate commands like `crawl_all_components.py`, `geocode_components.py`, etc.

### Search Optimization

To optimize search performance without updating data:

```bash
python optimize_search.py
```

## Command Options

The `update_database.py` script supports several options:

```bash
# Skip specific steps
python update_database.py --skip-import --skip-geocode

# Limit the number of components to process
python update_database.py --import-limit 100 --geocode-limit 200

# Specify a data source
python update_database.py --import-src path/to/data.json
```

## Redundant Files

The following files are now redundant and have been replaced by the consolidated scripts:

| Redundant File | Replacement |
|----------------|-------------|
| `crawl_all_components.py` | `update_database.py` |
| `cache_cmu.py` | `optimize_search.py` |
| `cache_data.py` | `optimize_search.py` |
| Multiple cache builders | `update_database.py` |

## Performance Tips

1. **Run the full update process nightly** to ensure data freshness
2. **Run the search optimization separately** during peak hours if needed
3. **Use the `--skip-*` options** to run only necessary update steps
4. **Consider increasing database connection pooling** for better performance
5. **Monitor your database performance** using Django Debug Toolbar

## Troubleshooting

### Update Process Errors

- **Import Errors**: Check data source format and availability
- **Geocoding Errors**: Verify Google Maps API key and usage limits
- **Search Index Errors**: Ensure PostgreSQL has the required extensions enabled
- **Cache Errors**: Check Redis connection and memory availability

### Performance Issues

- **Slow Searches**: Run `python optimize_search.py` to rebuild search index
- **High Memory Usage**: Adjust batch sizes using the `--import-limit` option
- **Slow Map Loading**: Run `python optimize_search.py` to rebuild map cache

## Database Maintenance

For optimal performance, occasionally run PostgreSQL maintenance:

```sql
-- Analyze tables for better query planning
ANALYZE checker_component;

-- Rebuild indexes for better performance
REINDEX TABLE checker_component;

-- Vacuum to reclaim space and update statistics
VACUUM ANALYZE checker_component;
```

## Next Steps

While these optimizations significantly improve performance, you might consider:

1. Implementing server-side caching with Redis or Memcached
2. Adding database-level materialized views for common queries
3. Setting up read replicas for high-traffic deployments
4. Implementing proper database partitioning for very large datasets