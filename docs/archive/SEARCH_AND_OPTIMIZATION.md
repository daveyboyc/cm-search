# Capacity Market Search Implementation and Optimization

This document provides a comprehensive overview of the search functionality implementation, optimizations, and future plans for the Capacity Market Registry project.

## 1. Current Capabilities

The search functionality provides:

- Full-text search across all component fields
- Location-based grouping with intelligent pagination
- Multiple sort options (relevance, location, date, capacity)
- Company search with Redis-backed optimizations
- Complex multi-word query handling
- PostgreSQL-backed search for optimal performance

## 2. Technical Implementation

### 2.1 Current Architecture (May 2025)

The search system now uses a two-model approach:

1. **Component Model**: Stores individual component records from auctions
2. **LocationGroup Model**: Pre-aggregated data by location for efficient search

#### LocationGroup Model Structure:
```python
- location (unique, indexed)
- component_count (indexed for sorting)
- capacity fields (displayed, normalized, confidence)
- JSON fields with GIN indexes:
  - companies: {"Company A": count, "Company B": count}
  - technologies: {"Battery": count, "Solar": count}
  - descriptions: [list of unique descriptions]
  - auction_years: [sorted list of years]
  - cmu_ids: [list of CMU IDs]
- Geographic fields (latitude, longitude, county, outward_code)
- is_active flag for filtering
```

### 2.2 Database Structure

The implementation uses PostgreSQL's full-text search capabilities via a `SearchVectorField` in the `Component` model:

```python
# Full-text search field
search_vector = SearchVectorField(null=True)
```

This field combines weighted text from different columns:
- Company name and location (weight A - highest priority)
- County and description (weight B - medium priority)
- Technology and CMU ID (weight C - lower priority)
- Other fields (weight D - lowest priority)

### 2.2 Database Indexing

For search performance, several indexes have been implemented:

1. **Full-text Search Index**: A GIN (Generalized Inverted Index) for the `search_vector` field:
   ```sql
   CREATE INDEX component_search_idx ON checker_component USING GIN(search_vector);
   ```

2. **Composite Indexes**:
   - Index covering (technology, company_name) for common combined searches
   - Index on (delivery_year, location) to speed up active/inactive filtering
   - Index on county and outward_code fields for improved location searches

3. **Geographical Fields**:
   - Indexes on latitude and longitude for map-based queries

### 2.3 Search Query Processing

The search implementation follows these steps:

1. **Query Analysis**:
   - Detect query type (CMU ID, location, company, general)
   - Expand location queries with postcode mappings
   - Apply appropriate search strategy based on query type

2. **Database Querying**:
   - For text searches: `Component.objects.filter(search_vector=SearchQuery('query'))`
   - For multi-word: `SearchQuery('query terms', config='english', search_type='websearch')`
   - For location searches: Custom location expansion with postcode mapping

3. **Result Ranking**:
   - Relevance ranking using PostgreSQL's ts_rank:
     ```python
     .annotate(rank=SearchRank(F('search_vector'), query))
     ```
   - Custom sorting by location, date, capacity, etc.

4. **Results Grouping**:
   - Group components by location and description
   - Preserve unique CMU IDs and auction information
   - Apply active/inactive status based on auction years

5. **Smart Pagination**:
   - Load more raw components than needed for proper grouping
   - Apply specialized handling for location-based sorting

## 3. Pagination for Grouped Results

The search system groups results by location and description, creating challenges for pagination since the number of groups doesn't directly correlate to the number of raw components.

### 3.1 Smart Component Multipliers

The system uses multipliers to fetch more raw components than needed to ensure proper grouping:
- Base multiplier: 5x (fetches 5 times more components than desired groups)
- Location-based sorting multiplier: 10x (increased from 7x to handle alphabetical distribution)
- Progressive scaling for higher page numbers using additional multipliers

### 3.2 Last Page Handling

Special consideration is given to last pages, which typically have fewer components per location group:
- For high page numbers, especially with location sorting, the system uses enhanced multipliers
- Dynamic adjustment of maximum components fetched based on page number and sort type
- Proper calculation of total pages after grouping to ensure "Last" page button works correctly

### 3.3 Adaptive Query Limits

- Normal searches: up to 1500 components per query
- Location-sorted high page numbers: up to 2000 components to ensure complete results
- Enhanced logging to diagnose edge cases and ratio of raw components to groups

## 4. Optimizations Implemented

### 4.1 Search Optimization (May 2024)

✅ **Pagination and Logging Optimizations**:
   - Increased raw component multiplier for location-based sorting from 7x to 10x
   - Enhanced component fetching for high page numbers with adaptive multipliers
   - Implemented higher fetch limits (up to 2000 components) for location sorting
   - Added smart page calculation to ensure proper "Last" page navigation
   - Fixed cached location sort ordering on last page
   - Implemented cache sort verification for the last page in location sorting
   - Added progressive cache timeouts (shorter for high-page location sorting)
   - Reduced de-rated capacity logging frequency from 1% to 0.1% of components
   - Changed to DEBUG level logging to minimize production log impact
   - Added detailed diagnostics for pagination troubleshooting

✅ **LocationGroup Model Implementation** (May 2025):
   - Replaced Redis-based company search with LocationGroup model
   - Pre-aggregated location data eliminates runtime grouping
   - Added GIN indexes on JSON fields for efficient searches:
     - companies, technologies, descriptions, auction_years, cmu_ids
   - Search queries LocationGroup directly instead of components
   - Removed ~1.6MB Redis memory usage from company index
   - Simplified architecture with database-driven approach

### 4.2 Database Optimizations

✅ **Composite Indexes**:
   - Added index covering (technology, company_name) for common combined searches
   - Created index on (delivery_year, location) to speed up active/inactive filtering
   - Added specialized indexes for county and outward_code to improve location-based searches

✅ **Query Optimization**:
   - Improved search_type_determination to better identify query intent
   - Optimized location expansion logic to reduce database round trips
   - Enhanced multi-word query handling for better relevance

## 5. Performance Metrics 

| Operation | Before Optimization | After Optimization | Improvement |
|-----------|---------------------|-------------------|-------------|
| Company search | ~2.9s | ~0.066s | 44x faster |
| Location-based sorting (last page) | Incomplete results | Complete results | Correctness |
| De-rated capacity logging | 1% of components | 0.1% of components | 90% reduction |
| Search page initial load | ~1.2s | ~0.8s | 33% faster |

## 6. Pending Optimizations

### 6.1 Performance Testing

- [ ] Implement comprehensive performance testing
  - Create load test scripts for common search scenarios
  - Benchmark location-based sorting with high page numbers
  - Compare response times between different sorting methods
  - Test pagination "Last" page performance across all sorting options
  - Document baseline performance metrics for future comparisons

### 6.2 Database Monitoring

- [ ] Add database query monitoring
  - Log query execution plans for complex searches
  - Track number of raw components vs. grouped results ratio
  - Implement automatic alerts for searches exceeding time thresholds
  - Add timing instrumentation for group_by_location function

### 6.3 Memory Optimization

- [ ] Optimize memory usage for large component sets
  - Review component data structure for optimization opportunities
  - Consider implementing pagination-aware caching for location sort
  - Evaluate memory consumption during high-volume searching

### 6.4 Search Enhancement

- [ ] Implement phonetic matching for better handling of name variations
- [ ] Add support for synonym dictionaries
- [ ] Implement autocomplete suggestions based on frequent search terms
- [ ] Add faceted search capabilities for filtering results
- [ ] Further refine pagination for grouped results and multi-field sorting

## 7. Current Performance Bottlenecks

### 7.1 Location Search Performance

The current implementation has several areas for optimization:

1. **Two-Step Query Process**:
   - First queries Component model to find matching locations
   - Then queries LocationGroup with those locations
   - Could be optimized to search LocationGroup directly

2. **JSON Field Performance**:
   - GIN indexes help but complex JSON queries can still be slow
   - Queries like `companies @> '{"Company Name": 1}'` require JSON parsing
   - Consider functional indexes on frequently searched JSON paths

3. **Postcode Expansion**:
   - Still uses in-memory Python dictionaries
   - Each postcode search requires Python-level expansion
   - Could benefit from database-level postcode mapping

4. **Location Detail View**:
   - Loads all components for a location without pagination
   - Multiple CMURegistry lookups without prefetching
   - Builds auction links dynamically on each request

### 7.2 Optimization Opportunities

1. **Add Full-Text Search to LocationGroup**:
   ```sql
   ALTER TABLE checker_locationgroup ADD COLUMN search_vector tsvector;
   CREATE INDEX location_group_search_idx ON checker_locationgroup USING GIN(search_vector);
   ```

2. **Create Functional Indexes**:
   ```sql
   CREATE INDEX idx_locationgroup_company_names ON checker_locationgroup 
   USING GIN ((companies::jsonb));
   ```

3. **Database Postcode Mapping**:
   - Create PostcodeArea model
   - Store postcode relationships in database
   - Enable SQL joins instead of Python expansion

4. **Optimize Detail View**:
   - Add pagination for component lists
   - Use prefetch_related for CMURegistry
   - Cache auction link generation

## 8. Usage

### 8.1 Running Migrations

To set up the search functionality, run:

```bash
python manage.py migrate
```

### 7.2 Rebuilding the Search Index

After migrating, rebuild the search index:

```bash
python manage.py rebuild_search_index
```

This command:
1. Updates the search vector for all existing records
2. Creates or updates the necessary database triggers
3. Verifies the database extensions (pg_trgm)

### 8.3 Cache Management

To rebuild the caches after removing Redis company search:

```bash
# Rebuild LocationGroup data
python manage.py build_location_groups

# For incremental updates (faster)
python manage.py build_location_groups_incremental

# Rebuild other Redis caches
./rebuild_redis_caches.sh
```

The rebuild script now:
1. Rebuilds the location-to-postcode mappings
2. Refreshes the CMU dataframe cache
3. (Company index no longer needed - using LocationGroup instead)