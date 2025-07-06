# Location Search Optimization Status

## Summary (May 2025)

The capacity market search has been migrated from a Redis-cached company search to a database-driven LocationGroup model approach. This change reduces Redis memory pressure and simplifies the architecture while maintaining performance.

## Key Changes

### 1. LocationGroup Model Implementation
- Created `LocationGroup` model to store pre-aggregated location data
- Each unique location has one record with aggregated component information
- Stores counts and lists for companies, technologies, descriptions, CMU IDs
- Includes capacity calculations and geographic data

### 2. GIN Indexes Added
- PostgreSQL GIN indexes on all JSON fields:
  - `companies`, `technologies`, `descriptions`, `auction_years`, `cmu_ids`
- Enables efficient searches within JSON data
- Migration: `0017_add_gin_indexes_to_locationgroup.py`

### 3. Redis Company Search Removed
- Eliminated ~1.6MB Redis usage from company index
- Search now queries database directly
- Simplified architecture with fewer moving parts

## Current Performance Bottlenecks

### 1. Two-Step Query Process
**Issue**: Location search first queries Component model, then LocationGroup
```python
# Current approach in location_search.py
matching_locations = Component.objects.filter(
    component_filter
).values_list('location', flat=True).distinct()

queryset = LocationGroup.objects.filter(location__in=matching_locations)
```

**Solution**: Add full-text search directly to LocationGroup model

### 2. JSON Query Performance
**Issue**: Complex JSON queries can be slow despite GIN indexes
```python
# Example slow query
LocationGroup.objects.filter(companies__contains={'Company Name': 1})
```

**Solution**: Add functional indexes on frequently searched JSON paths

### 3. Postcode Expansion
**Issue**: Uses in-memory Python dictionaries for postcode mapping
```python
postcodes = get_all_postcodes_for_area(query)  # Python-level expansion
```

**Solution**: Move postcode data to database for SQL-level joins

### 4. Location Detail View
**Issue**: Loads all components without pagination, multiple CMURegistry lookups
```python
components = Component.objects.filter(location=location_group.location)
# Then loops through all components building auction links
```

**Solution**: Add pagination and use prefetch_related

## Recommended Next Steps

### 1. Add Full-Text Search to LocationGroup
```sql
ALTER TABLE checker_locationgroup ADD COLUMN search_vector tsvector;

UPDATE checker_locationgroup 
SET search_vector = to_tsvector('english',
    location || ' ' || 
    COALESCE((SELECT string_agg(key, ' ') FROM jsonb_each_text(companies)), '') || ' ' ||
    COALESCE((SELECT string_agg(key, ' ') FROM jsonb_each_text(technologies)), '')
);

CREATE INDEX location_group_search_idx ON checker_locationgroup USING GIN(search_vector);
```

### 2. Create Functional Indexes
```sql
-- Index for company name searches
CREATE INDEX idx_lg_company_keys ON checker_locationgroup 
USING GIN ((companies::jsonb));

-- Index for technology searches  
CREATE INDEX idx_lg_tech_keys ON checker_locationgroup
USING GIN ((technologies::jsonb));
```

### 3. Implement Database Postcode Mapping
```python
class PostcodeArea(models.Model):
    area_code = models.CharField(max_length=10, unique=True)  # e.g., "SW11"
    postcodes = models.JSONField(default=list)  # ["SW11 1", "SW11 2", ...]
    
    class Meta:
        indexes = [
            models.Index(fields=['area_code']),
        ]
```

### 4. Optimize Location Detail View
```python
# Use prefetch_related
cmu_ids = location_group.cmu_ids
registry_entries = CMURegistry.objects.filter(
    cmu_id__in=cmu_ids
).in_bulk(field_name='cmu_id')

# Add pagination
from django.core.paginator import Paginator
components = Component.objects.filter(location=location_group.location)
paginator = Paginator(components, 50)
```

## Performance Metrics

| Operation | Before (Redis) | Current (LocationGroup) | Target |
|-----------|---------------|------------------------|---------|
| Company search | ~0.066s | ~0.15s | ~0.10s |
| Location search | N/A | ~0.20s | ~0.15s |
| Memory usage | 1.6MB (Redis) | 0MB | 0MB |
| Architecture complexity | High | Medium | Low |

## Migration Commands

```bash
# Build initial LocationGroup data
python manage.py build_location_groups

# Incremental updates
python manage.py build_location_groups_incremental

# Check status
python manage.py check_location_group_status
```

## Monitoring

Key metrics to track:
- LocationGroup query time
- JSON field query performance
- Location detail page load time
- Database connection pool usage

## Conclusion

The move from Redis to LocationGroup has successfully reduced memory pressure and simplified the architecture. The main optimization opportunities now lie in:
1. Direct LocationGroup searching (avoid Component model query)
2. Better JSON indexing strategies
3. Database-level postcode mapping
4. Pagination and prefetching in detail views

These optimizations should bring search performance back to or better than the Redis-cached levels while maintaining the simpler architecture.