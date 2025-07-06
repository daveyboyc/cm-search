# Location Search Performance Optimization Plan

## Current Performance Issues

After removing Redis dependency for company search and implementing GIN indexes, location search remains the primary performance bottleneck.

### Identified Bottlenecks

1. **Two-Step Search Process**
   - Current flow: LocationGroup search → Component search (if <3 results) → Map back to LocationGroups
   - This creates multiple database round-trips
   - Component model has 89,000+ records vs LocationGroup's 16,000

2. **Inefficient JSON Field Queries**
   - Using `Q(companies__icontains=query)` searches entire JSON structure
   - PostgreSQL must scan all JSON content even with GIN indexes
   - Multiple OR conditions create complex query plans

3. **Postcode Expansion Overhead**
   - Still uses Python-level postcode expansion via static files
   - Creates large OR queries for area searches (e.g., "peckham" → 2 postcodes)
   - Cannot leverage database indexes effectively

4. **Missing Search Vectors**
   - No full-text search on LocationGroup model
   - Component model has search_vector but LocationGroup doesn't
   - Cannot use PostgreSQL's powerful text search capabilities

## Proposed Optimizations

### 1. Add Full-Text Search to LocationGroup (High Priority)

Create a search vector field combining all searchable content:

```python
# In LocationGroup model
from django.contrib.postgres.search import SearchVectorField

class LocationGroup(models.Model):
    # ... existing fields ...
    search_vector = SearchVectorField(null=True)
```

Migration to populate it:
```sql
UPDATE checker_locationgroup
SET search_vector = to_tsvector('english',
    COALESCE(location, '') || ' ' ||
    COALESCE(county, '') || ' ' ||
    COALESCE(outward_code, '') || ' ' ||
    COALESCE(array_to_string(ARRAY(SELECT jsonb_object_keys(companies)), ' '), '') || ' ' ||
    COALESCE(technologies::text, '') || ' ' ||
    COALESCE(descriptions::text, '')
);

CREATE INDEX locationgroup_search_idx ON checker_locationgroup USING GIN(search_vector);
```

Then search becomes:
```python
from django.contrib.postgres.search import SearchQuery

search_query = SearchQuery(query)
location_groups = LocationGroup.objects.filter(search_vector=search_query)
```

**Expected Impact**: 5-10x faster searches, eliminates Component fallback

### 2. Create Functional Indexes on JSON Fields (Medium Priority)

Add specific indexes for common JSON queries:

```sql
-- Index for company name searches
CREATE INDEX locationgroup_company_names_idx ON checker_locationgroup 
USING GIN ((companies::text) gin_trgm_ops);

-- Index for technology searches  
CREATE INDEX locationgroup_tech_idx ON checker_locationgroup
USING GIN ((technologies::text) gin_trgm_ops);

-- Index for descriptions
CREATE INDEX locationgroup_desc_idx ON checker_locationgroup
USING GIN ((descriptions::text) gin_trgm_ops);
```

This enables trigram similarity searches on JSON content.

### 3. Database-Level Postcode Mapping (Medium Priority)

Create a PostcodeArea model:

```python
class PostcodeArea(models.Model):
    area_name = models.CharField(max_length=100, db_index=True)
    outward_code = models.CharField(max_length=4, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['area_name', 'outward_code']),
        ]
```

Then area searches become:
```python
# Instead of Python-level expansion
area_postcodes = PostcodeArea.objects.filter(
    area_name__iexact=query
).values_list('outward_code', flat=True)

location_groups = LocationGroup.objects.filter(
    outward_code__in=area_postcodes
)
```

**Expected Impact**: Eliminates Python postcode expansion, enables SQL joins

### 4. Optimize Query Patterns (High Priority)

Simplify the search logic:

```python
def search_locations_optimized(query):
    # Use full-text search if available
    if hasattr(LocationGroup, 'search_vector'):
        from django.contrib.postgres.search import SearchQuery, SearchRank
        
        search_query = SearchQuery(query)
        location_groups = LocationGroup.objects.annotate(
            rank=SearchRank('search_vector', search_query)
        ).filter(search_vector=search_query).order_by('-rank')
    else:
        # Fallback to current approach but optimized
        # Use a single complex query instead of multiple steps
        from django.db.models import Q, Value
        from django.db.models.functions import Concat
        
        # Create a searchable text field on the fly
        location_groups = LocationGroup.objects.annotate(
            searchable_text=Concat(
                'location', Value(' '),
                'county', Value(' '),
                'outward_code'
            )
        ).filter(
            Q(searchable_text__icontains=query) |
            Q(companies__has_key=query) |  # Exact company match
            Q(technologies__contains=[query]) |  # Technology array contains
            Q(cmu_ids__contains=[query])  # CMU ID array contains
        )
    
    return location_groups
```

### 5. Implement Materialized Views (Low Priority)

For complex aggregations, use PostgreSQL materialized views:

```sql
CREATE MATERIALIZED VIEW location_search_view AS
SELECT 
    lg.id,
    lg.location,
    lg.normalized_capacity_mw,
    lg.component_count,
    -- Flatten JSON for easier searching
    string_agg(DISTINCT company_name, ' ') as all_companies,
    string_agg(DISTINCT tech, ' ') as all_technologies,
    -- Create searchable text
    lg.location || ' ' || 
    lg.county || ' ' || 
    lg.outward_code || ' ' ||
    string_agg(DISTINCT company_name, ' ') || ' ' ||
    string_agg(DISTINCT tech, ' ') as search_text
FROM checker_locationgroup lg,
    jsonb_object_keys(lg.companies) as company_name,
    jsonb_array_elements_text(lg.technologies) as tech
GROUP BY lg.id, lg.location, lg.normalized_capacity_mw, lg.component_count;

CREATE INDEX location_search_view_text_idx ON location_search_view 
USING GIN(to_tsvector('english', search_text));
```

### 6. Cache Common Searches (Low Priority)

Since LocationGroup data changes infrequently, cache common search results:

```python
from django.core.cache import cache

def search_with_cache(query):
    cache_key = f"location_search:{query.lower()}"
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    # Perform search
    results = search_locations_optimized(query)
    
    # Cache for 1 hour
    cache.set(cache_key, list(results.values_list('id', flat=True)), 3600)
    
    return results
```

## Implementation Priority

1. **Immediate (1-2 hours)**:
   - Simplify query patterns to avoid Component fallback
   - Use more efficient JSON queries with has_key instead of icontains

2. **Short-term (4-6 hours)**:
   - Add SearchVectorField to LocationGroup
   - Create migration to populate search vectors
   - Update search logic to use full-text search

3. **Medium-term (1-2 days)**:
   - Create PostcodeArea model and migrate data
   - Add functional indexes on JSON fields
   - Implement query result caching

4. **Long-term (optional)**:
   - Create materialized views for complex searches
   - Implement search analytics to identify common patterns
   - Consider Elasticsearch for advanced search features

## Expected Performance Improvements

- **Current**: Location searches take 2-5 seconds
- **After optimization**: Target <500ms for most searches
- **Complex searches**: Target <1 second
- **Cached searches**: <50ms

## Monitoring and Metrics

Add timing logs to track improvements:

```python
import time
import logging

logger = logging.getLogger(__name__)

def search_with_timing(query):
    start = time.time()
    
    # ... perform search ...
    
    duration = time.time() - start
    logger.info(f"Location search for '{query}': {duration:.3f}s")
    
    # Track slow queries
    if duration > 1.0:
        logger.warning(f"Slow location search: '{query}' took {duration:.3f}s")
```

## Next Steps

1. Create migrations for SearchVectorField
2. Update search service to use new optimized queries
3. Add performance monitoring
4. Test with common search patterns
5. Deploy and monitor improvements