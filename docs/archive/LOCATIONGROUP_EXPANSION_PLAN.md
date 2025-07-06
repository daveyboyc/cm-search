# LocationGroup Expansion Plan

## Overview
Extend the high-performance LocationGroup-based search to all major views in the platform, achieving consistent sub-2 second response times across the board.

## Current State
- ✅ Main search (`/search-optimized-v2/`) - Working with LocationGroup
- ❌ Technology pages (`/technology/<tech_name>/`)
- ❌ Company pages (`/company/<company_id>/`)
- ❌ CMU ID pages (doesn't exist yet)
- ❌ Map view integration

## Implementation Plan

### Phase 1: Technology Pages
**Goal**: Convert technology pages to use LocationGroup for fast filtering

1. **Create optimized technology view**
   - File: `checker/views_technology_optimized.py`
   - Function: `technology_detail_optimized(request, technology_name)`
   - Logic:
     ```python
     # Find all LocationGroups containing this technology
     location_groups = LocationGroup.objects.filter(
         technologies__has_key=technology_name
     ).order_by('-normalized_capacity_mw')
     ```

2. **Update URL routing**
   - Add: `path('technology-optimized/<str:technology_name>/', views_technology_optimized.technology_detail_optimized, name='technology_detail_optimized')`

3. **Create optimized template**
   - File: `checker/templates/checker/technology_detail_optimized.html`
   - Reuse the same result item structure from search_locationgroup_optimized.html

### Phase 2: Company Pages
**Goal**: Convert company pages to use LocationGroup for fast filtering

1. **Create optimized company view**
   - File: `checker/views_company_optimized.py`
   - Function: `company_detail_optimized(request, company_id)`
   - Logic:
     ```python
     # Find all LocationGroups containing this company
     location_groups = LocationGroup.objects.filter(
         companies__has_key=company_name
     ).order_by('-normalized_capacity_mw')
     ```

2. **Update URL routing**
   - Add: `path('company-optimized/<str:company_id>/', views_company_optimized.company_detail_optimized, name='company_detail_optimized')`

3. **Create optimized template**
   - File: `checker/templates/checker/company_detail_optimized.html`
   - Include company summary stats at top
   - Reuse location result structure

### Phase 3: CMU ID Pages (New Feature)
**Goal**: Create new CMU-based views showing all locations for a CMU

1. **Create CMU detail view**
   - File: `checker/views_cmu_optimized.py`
   - Function: `cmu_detail_optimized(request, cmu_id)`
   - Logic:
     ```python
     # Find all LocationGroups containing this CMU ID
     location_groups = LocationGroup.objects.filter(
         cmu_ids__contains=cmu_id
     ).order_by('location')
     ```

2. **Add URL routing**
   - Add: `path('cmu/<str:cmu_id>/', views_cmu_optimized.cmu_detail_optimized, name='cmu_detail')`

3. **Create CMU template**
   - File: `checker/templates/checker/cmu_detail.html`
   - Show CMU summary (total capacity, technology mix, etc.)
   - List all locations with their components

### Phase 4: Map View Integration
**Goal**: Add "View on Map" functionality to optimized views

1. **Add map data to LocationGroup model**
   - Already has: `latitude`, `longitude` fields
   - Need to ensure these are populated during build process

2. **Create map data endpoint**
   - File: `checker/views_map_api.py`
   - Function: `get_locationgroup_map_data(request)`
   - Returns GeoJSON from LocationGroup queryset

3. **Add map integration to templates**
   - Add "View on Map" button to search results
   - Pass LocationGroup IDs to map view
   - Create `map_locationgroups.html` template

### Phase 5: Migration Strategy
**Goal**: Gradually migrate users to optimized views

1. **A/B Testing Approach**
   - Add feature flag: `USE_OPTIMIZED_VIEWS`
   - Redirect percentage of users to optimized versions
   - Monitor performance and errors

2. **Update all internal links**
   - Company badges → optimized company pages
   - Technology badges → optimized technology pages
   - CMU references → new CMU pages

3. **Performance Monitoring**
   - Track response times for each view type
   - Compare optimized vs. original performance
   - Monitor LocationGroup coverage percentage

## Technical Considerations

### 1. LocationGroup Data Completeness
- Current coverage: ~83% (needs to reach 100%)
- Run: `python manage.py build_location_groups --complete`
- Add scheduled task to keep LocationGroups updated

### 2. Shared Components
- Create `checker/templates/checker/components/_locationgroup_result.html`
- Reusable component for displaying LocationGroup results
- Consistent styling across all views

### 3. Search within Views
- Add search bars to technology/company/CMU pages
- Filter within the current context (e.g., search within a technology)

### 4. Caching Strategy
- Cache technology/company aggregations in Redis
- Cache map data for frequently accessed queries
- Use cache warming for popular pages

### 5. API Endpoints
- `/api/technology/<name>/locations/` - Get LocationGroups for technology
- `/api/company/<id>/locations/` - Get LocationGroups for company
- `/api/cmu/<id>/locations/` - Get LocationGroups for CMU
- `/api/map/locationgroups/` - Get map data for LocationGroup IDs

## Implementation Order
1. Complete LocationGroup data (reach 100% coverage)
2. Technology pages (most straightforward)
3. Company pages (similar to technology)
4. CMU pages (new feature, high value)
5. Map integration (enhances all views)

## Expected Performance Improvements
- Technology pages: 5-10s → <1s
- Company pages: 3-8s → <1s  
- CMU pages: N/A → <1s
- Map data loading: 10-20s → <2s

## Success Metrics
- All major views load in <2 seconds
- 100% LocationGroup coverage
- Consistent UI/UX across all views
- Map integration on all list views
- Reduced database query count by 90%+