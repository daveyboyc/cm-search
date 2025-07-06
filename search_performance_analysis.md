# Search Performance Analysis for "boots" Query

## Issue Summary
The search for "boots" is taking 3.1 seconds in production despite showing "0 database queries" in the log. Local testing shows it's actually taking 4-5 seconds.

## Root Causes Identified

### 1. Inefficient Text Search on Location Field
- The `location__icontains` search alone takes 4.5 seconds
- Despite having a B-tree index on location, `ILIKE '%boots%'` queries cannot use it efficiently
- The query has to scan all 16,009 LocationGroup records

### 2. Multiple ILIKE Operations on Large Text/JSON Fields
The search performs 6 ILIKE operations:
- location__icontains (varchar field) - 4.5s
- county__icontains (varchar field) - 0.9s  
- companies__icontains (JSONB cast to text) - 0.1s
- technologies__icontains (JSONB cast to text) - 0.05s
- descriptions__icontains (JSONB cast to text) - 0.08s
- cmu_ids__icontains (JSONB cast to text) - 0.07s

### 3. Network Latency
- The database query itself only takes 31ms in Supabase
- But the round-trip from Django to Supabase adds significant overhead
- This explains why it shows "0 database queries" - Django's query counter doesn't count remote database time

### 4. Missing Trigram Indexes
- PostgreSQL's pg_trgm extension is enabled but not being used
- No GIN trigram indexes exist on text fields for fast ILIKE searches

## Recommended Optimizations

### 1. Add Trigram Indexes (Immediate Fix)
Created migration `0024_add_trgm_indexes.py` to add GIN trigram indexes:
```sql
CREATE INDEX locationgroup_location_trgm_idx ON checker_locationgroup USING GIN (location gin_trgm_ops);
CREATE INDEX locationgroup_county_trgm_idx ON checker_locationgroup USING GIN (county gin_trgm_ops);
```
This should reduce search time from 4.5s to <100ms.

### 2. Implement Search Result Caching
Cache frequent searches like "boots" in Redis:
```python
cache_key = f"search_results:{query}:{page}:{filters_hash}"
results = cache.get(cache_key)
if not results:
    results = perform_search()
    cache.set(cache_key, results, timeout=300)  # 5 minutes
```

### 3. Use Full-Text Search
For even better performance, implement PostgreSQL full-text search:
```python
# Add a search vector field
search_vector = SearchVector('location', 'county', 'companies', 'descriptions')

# Use full-text search
LocationGroup.objects.annotate(
    search=search_vector
).filter(search=query)
```

### 4. Optimize JSONB Searches
Instead of casting JSONB to text for ILIKE:
```python
# Current (slow):
Q(companies__icontains=query)  # Casts to text

# Better:
Q(companies__has_key=query)  # Uses GIN index
```

### 5. Consider Elasticsearch/Algolia
For production search at scale, consider dedicated search infrastructure.

## Performance Impact
- Current: 3-5 seconds per search
- With trigram indexes: <500ms
- With caching: <50ms for cached searches
- With full-text search: <100ms consistently

## Egress Impact
Each search currently fetches ~25 LocationGroup records with all fields. Consider selecting only needed fields to reduce Supabase egress usage.