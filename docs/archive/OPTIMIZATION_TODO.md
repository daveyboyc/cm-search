# Capacity Market Search - Optimization TODO

This document outlines optimization strategies to reduce egress costs, improve performance, and enhance user experience.

## Recently Implemented Optimizations (May 2025)

✅ **LocationGroup Model Implementation**: Replaced runtime component grouping with database-driven approach:
   - Created LocationGroup model for pre-aggregated location data
   - Eliminated expensive runtime component grouping in favor of pre-computed groups
   - Added GIN indexes on JSON fields (companies, technologies, descriptions, etc.)
   - Search now queries LocationGroup model directly instead of components
   - Added is_active field for database-level active/inactive determination
   - Simplified architecture by moving from runtime calculations to database queries

✅ **Company Search Optimization**: Removed Redis dependency for company search:
   - Replaced Redis-cached company index with direct PostgreSQL queries
   - Uses jsonb_object_keys() to extract company names from LocationGroup
   - Eliminates ~5MB Redis usage and cache rebuild complexity
   - Performance improved due to GIN indexes and small dataset (~1600 companies)
   - Removed network round-trip and serialization overhead

✅ **Static JSON Files for Location Mappings**: Replaced 71.5GB Redis location mappings:
   - Moved postcode mappings to 3MB static JSON files
   - 560x faster location lookups (5.6s → <10ms)
   - Eliminated massive Redis memory pressure
   - Location lookups now use in-memory static data

## Recently Implemented Optimizations (May 2024)

✅ **Pagination and Logging Optimizations**: Improved search results pagination and reduced logging verbosity:
   - Increased raw component multiplier for location-based sorting from 7x to 10x
   - Enhanced component fetching for high page numbers with adaptive multipliers
   - Implemented higher fetch limits (up to 2000 components) for location sorting
   - Added smart page calculation to ensure proper "Last" page navigation
   - Reduced de-rated capacity logging frequency from 1% to 0.1% of components
   - Changed to DEBUG level logging to minimize production log impact
   - Added detailed diagnostics for pagination troubleshooting

## Recently Implemented Optimizations (April 2024)

✅ **Robust Map Data Caching System**: Implemented a multi-level caching system for map data:
   - Django's built-in cache framework (LocMemCache in development, configurable via settings)
   - File-based cache fallback for reliability during development
   - Detailed cache key generation based on request parameters
   - Cache debugging and verification
   - Performance tracking for each processing stage

✅ **Client-Side Map Data Caching**: Added browser-side caching for map data:
   - JavaScript cache object to store map responses by region/filters
   - Cache key generation based on request parameters
   - Cache expiration and size management
   - Cache hit/miss statistics tracking
   - Visual indicators for cached vs fetched data

✅ **Performance Monitoring**: Added detailed timing and performance metrics:
   - Server-side stage-by-stage timing for map data processing
   - Client-side render timing for marker display
   - Cache hit/miss rate visualization
   - Detailed logging for performance bottleneck identification

## Already Implemented Optimizations

✅ Backend query optimization using `.values()` to fetch only needed fields (e.g., in `get_components_from_database`)  
✅ Frontend "select technology first" pattern to avoid loading all data on initial map view  
✅ Conditional overlay creation based on zoom level  
✅ Debouncing idle events to prevent repeated API calls during map navigation
✅ Basic database indexing on key fields (`db_index=True`)  
✅ Basic spatial indexing (`latitude`, `longitude`)  
✅ Initial map load uses minimal data (`detail_level=minimal`)  
✅ Component map detail API (`/api/component-map-detail/<id>/`)  
✅ Map marker click loads details via API  
✅ Basic user registration with email/password (`accounts` app)  
✅ Theme switcher (light/dark/auto)  

## High-Priority Optimizations / Tasks

### 1. Map API Caching (Backend)

**Files to Examine:**
- `checker/views.py` - Specifically the `map_data_api` function
- `capacity_checker/settings.py` - Check cache settings

**Findings:**
- Django cache framework configured with `LocMemCache` (dev) or `DatabaseCache` (prod - commented out)
- Caching logic is implemented within `map_data_api` using a custom key.

**Recommended Actions:**
- **Verify Cache Effectiveness:** Monitor cache hits/misses in production or using `django-debug-toolbar` to ensure the custom key generation is working as expected across different filter combinations.
- **Consider Redis for Production:** Evaluate moving from `DatabaseCache` to Redis (using `django-redis`) on Heroku for better performance if the database cache becomes a bottleneck.

**Expected Impact:** High (if cache hits are frequent)

### 2. Progressive Detail Loading (Frontend - Refinement)

**Files to Examine:**
- `checker/templates/checker/map.html` - `loadComponentDetails` function

**Findings:**
- Basic mechanism is in place: click marker -> fetch details via API.

**Recommended Actions:**
- **Error Handling:** Improve user feedback if the detail API call fails (e.g., specific error message, retry option).
- **Pre-fetching (Optional):** Consider pre-fetching details for nearby markers when the user pauses map navigation, potentially reducing perceived latency on click (requires careful implementation to avoid excessive requests).

**Expected Impact:** Low-Medium (UI/UX refinement)

### 3. User Authentication Enhancements

**Files:** `accounts/` app, `checker/templates/checker/base.html`, `capacity_checker/settings.py`

**Findings:**
- Basic registration implemented.
- Email used as username internally.
- No email confirmation or password reset yet.

**Recommended Actions:**
- **Email Confirmation:**
    - ✅ Send activation email (console backend configured for dev).  
    - ✅ Implement `activate` view logic.  
    - 🚧 Add `registration_pending` view, template, and URL.  
    - 🚧 Add `activation_failed` view, template, and URL.  
    - 🚧 Configure production email backend (e.g., SendGrid, Mailgun) in `settings.py` with API keys/credentials (use environment variables!).
    - 🚧 Set `DEFAULT_FROM_EMAIL` in `settings.py`.  
- **Password Reset:**
    - 🚧 Create templates for Django's built-in password reset views (`registration/password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`).
    - 🚧 Ensure URLs for password reset are included (likely part of `django.contrib.auth.urls` already included at `/accounts/`).
    - 🚧 Configure email backend (same as confirmation).
- **Login/Logout Flow:**
    - 🚧 Set `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` in `settings.py` to redirect users appropriately after login/logout (e.g., to home or dashboard).
    - 🚧 Create `registration/logged_out.html` template (used by default logout view).

**Expected Impact:** Medium (Core Functionality)

### 4. Database Query/Data Integrity

**Files:** `checker/views.py`, `checker/services/`

**Findings:**
- Some search views (`technology_search_results`, general `q` search) were initially missing `location`/`description` or `db_id` due to data preparation differences or optimization attempts.
- `component_search.py` `format_component_record` needs careful handling of dictionary keys vs model attributes.

**Recommended Actions:**
- **Review Data Consistency:** Ensure that all views preparing component lists for the `search.html` template provide a consistent data structure (preferably dictionaries with consistent keys like `id`, `location`, `description`, `technology`, etc.) to simplify template logic.
- **Data Correction:** Investigate why some `Component` records seem to be missing `location` or `description` data in the database. Implement data cleaning/update scripts if necessary.
- **CMU ID Search:** Double-check the logic in `search_components_service` and `get_components_from_database` specifically for `search_type='cmu_id'` to ensure it correctly uses the filter and retrieves all necessary fields.

**Expected Impact:** Medium-High (Correctness, Reliability)

## Medium-Priority Optimizations

### 1. Redis-based Map Data Caching

**Files to Examine:**
- `checker/views.py` (Specifically the `map_data_api` function)
- `checker/templates/checker/map.html` (Client-side marker handling)

**Recommended Actions:**
- Implement cached map tile data based on viewport and filters:
  ```python
  def map_data_api(request):
      # Generate cache key based on viewport + filters
      viewport = f"{north}_{south}_{east}_{west}"
      filters = f"{technology}_{company}_{year}"
      cache_key = f"map_tile:{viewport}:{filters}"
      
      # Try Redis cache first
      cached_data = cache.get(cache_key)
      if cached_data:
          return HttpResponse(cached_data, content_type="application/json")
          
      # Otherwise generate and cache the data
      markers = fetch_markers_for_viewport(...)
      response = json.dumps(markers)
      cache.set(cache_key, response, timeout=3600*24)
      return HttpResponse(response, content_type="application/json")
  ```
- Create pre-clustered data at different zoom levels:
  ```python
  # Add management command
  def build_marker_clusters():
      zoom_levels = [6, 8, 10, 12, 14]
      for zoom in zoom_levels:
          grid_size = get_grid_size_for_zoom(zoom)
          clusters = cluster_components_by_grid(grid_size)
          cache.set(f"map_clusters:zoom_{zoom}", clusters, timeout=None)
  ```
- Pre-render marker detail HTML to avoid detail queries:
  ```python
  # Similar to company index, pre-render marker detail HTML
  def build_component_detail_cache():
      components = Component.objects.all()
      for component in components:
          detail_html = render_to_string('marker_detail.html', {'component': component})
          cache.set(f"marker_detail:{component.id}", detail_html, timeout=3600*24*7)
  ```
- Add PostgreSQL geographic optimizations:
  ```python
  # Add to models.py
  from django.contrib.postgres.indexes import GistIndex

  class Meta:
      indexes = [
          GistIndex(fields=['location_point']),  # If using PostGIS Point field
          models.Index(fields=['latitude', 'longitude']),
      ]
  ```

**Expected Impact:** High
- Reduced query load: 60-90% fewer database queries
- Faster rendering: Map view load time decreasing from 1-2s to ~200ms
- Lower egress costs from database
- Better user experience with near-instant marker loading and detail display

### 2. Frontend Data Caching and State Management

**Files to Examine:**
- `checker/templates/checker/map.html`

**Recommended Actions:**
- Implement client-side caching of previously fetched map regions:
  ```javascript
  // Add a simple cache object to store responses by region
  const mapDataCache = {};
  
  function loadMarkers(overrideTechnology = null) {
      // ...existing code...
      
      // Check if we have cached data for this region and parameters
      const cacheKey = `${technology}_${company}_${year}_${cmuId}_${north}_${south}_${east}_${west}`;
      if (mapDataCache[cacheKey]) {
          // Process and display cached data
          processMapData(mapDataCache[cacheKey]);
          return;
      }
      
      // Fetch from API if not cached
      fetch(fetchUrl)
          .then(/* ... */)
          .then(data => {
              // Cache the response
              mapDataCache[cacheKey] = data;
              // Process and display data
              processMapData(data);
          });
  }
  
  // Extract the data processing logic into a separate function
  function processMapData(data) {
      // ... existing marker creation code ...
  }
  ```
- Implement cache expiration/invalidation mechanism:
  ```javascript 
  // Clear cache when filters are reset or after certain time
  function resetFilters() {
      // Clear the client-side cache when filters change significantly
      mapDataCache = {};
      // ...existing code...
  }
  ```

**Expected Impact:** Medium
- Reduces duplicate API requests during a user session
- Improves perceived performance when revisiting the same map areas

### 3. Data Compression (Backend)

**Files to Examine:**
- `capacity_checker/settings.py`

**Findings:**
- `GZipMiddleware` is not currently enabled in the MIDDLEWARE list
- WhiteNoise is already configured for static file compression

**Recommended Actions:**
- Enable gzip compression by adding `GZipMiddleware` to Django settings:
  ```python
  # Add to settings.py MIDDLEWARE list (near the top, after SecurityMiddleware)
  MIDDLEWARE = [
      "django.middleware.security.SecurityMiddleware",
      "django.middleware.gzip.GZipMiddleware",  # Add this line
      "whitenoise.middleware.WhiteNoiseMiddleware",
      # ... other middleware
  ]
  ```
- Consider implementing custom JSON serialization optimizations:
  1. Shorten field names in API responses
  2. Omit null/empty values
  3. Use numeric or abbreviated values where possible

**Expected Impact:** Medium
- Immediate reduction in API response sizes (typically 60-80% smaller)
- Less network transfer time
- Lower bandwidth costs

### 4. Batch Fetching for Legend (Frontend)

**Files to Examine:**
- `checker/templates/checker/map.html`
- `checker/views.py`

**Recommended Actions:**
- Create a lightweight API endpoint for technology counts:
  ```python
  def technology_counts_api(request):
      # Apply viewport and other filters similar to map_data_api
      # Return counts per technology without full component data
      counts = Component.objects.filter(...) \
                        .values('technology') \
                        .annotate(count=Count('id'))
      return JsonResponse({'counts': list(counts)})
  ```
- Update the legend initialization to use this endpoint:
  ```javascript
  function updateLegendCounts() {
      fetch('/api/technology-counts/?' + params.toString())
          .then(response => response.json())
          .then(data => {
              // Update legend counts with data
          });
  }
  ```

**Expected Impact:** Medium
- Decouples legend data from marker data
- Allows for efficient count display without fetching all component details

### Phase 4: Code Quality and Monitoring
1. Refactor map code into modules/classes
2. Add performance tracking
3. Consider Advanced Markers migration

### Phase 5: Search and UX Improvements
1. Improve Fuzzy Search Accuracy (Tune RapidFuzz, Field-Specific Strategies)
2. Implement Persistent Sorting for Search Results

## Prioritized Implementation Checklist

Below is a prioritized list of specific changes to implement for optimizing the map functionality, ordered by expected impact vs. implementation effort:

### 1. Add Indexing for Geographical Fields (1-2 hours) ✅

* [x] Edit `checker/models.py` to add indexes:
  ```python
  # Update these fields:
  latitude = models.FloatField(null=True, blank=True, db_index=True)  # Add db_index=True
  longitude = models.FloatField(null=True, blank=True, db_index=True)  # Add db_index=True
  
  # Add to Meta class indexes list:
  models.Index(fields=['latitude', 'longitude'], name='spatial_idx'),
  ```
* [x] Create the migration: `python manage.py makemigrations`
* [x] Apply the migration: `python manage.py migrate`
* [x] Verify indexes: `curl http://localhost:8000/debug/indexes/`

### 2. Enable GZip Compression (15-30 minutes) ✅

* [x] Edit `capacity_checker/settings.py` to add GZipMiddleware:
  ```python
  MIDDLEWARE = [
      "django.middleware.security.SecurityMiddleware",
      "django.middleware.gzip.GZipMiddleware",  # Add this line
      "whitenoise.middleware.WhiteNoiseMiddleware",
      # ... rest of middleware ...
  ]
  ```
* [x] Restart the server and test
* [x] Verify compression is working using browser dev tools Network tab (check response headers for `Content-Encoding: gzip`)

### 3. Implement API Response Caching (1-2 hours) ✅

* [x] Edit `checker/views.py` to add comprehensive caching to the map data API:
  ```python
  from django.core.cache import cache
  import hashlib, json
  
  def map_data_api(request):
      # Create a deterministic cache key based on request parameters
      params = request.GET.copy()
      relevant_params = ['technology', 'north', 'south', 'east', 'west', 'company', 'year', 'cmu_id', 'detail_level', 'include_2024']
      filtered_params = {k: params.get(k, '') for k in relevant_params if k in params}
      
      # Create a stable hash for the parameters
      params_string = json.dumps(sorted(filtered_params.items()))
      params_hash = hashlib.md5(params_string.encode('utf-8')).hexdigest()
      cache_key = f"map_data_{params_hash}"
      
      # Try to get cached response from Django cache
      cached_response = cache.get(cache_key)
      if cached_response and isinstance(cached_response, str):
          return HttpResponse(cached_response, content_type="application/json")
      
      # Also implement file-based cache as fallback
      cache_file = os.path.join(cache_dir, f"{cache_key}.json")
      if os.path.exists(cache_file):
          # Check if file is newer than cache timeout
          if time.time() - os.path.getmtime(cache_file) < 3600:
              with open(cache_file, 'r') as f:
                  return HttpResponse(f.read(), content_type="application/json")
      
      # ... process data if not cached ...
      
      # Store response in both Django cache and file system
      json_str = json.dumps(response_data)
      cache.set(cache_key, json_str, 3600)  # Cache for 1 hour
      
      # Also use direct file-based caching as a backup
      with open(cache_file, 'w') as f:
          f.write(json_str)
      
      return HttpResponse(json_str, content_type="application/json")
  ```
* [x] Configure Django's cache settings for development and production:
  ```python
  # Development: Use LocMemCache
  CACHES = {
      'default': {
          'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
          'LOCATION': 'unique-snowflake',
          'TIMEOUT': 3600,  # 1 hour timeout
      }
  }
  
  # Production: Use DatabaseCache or consider Redis
  # CACHES = {
  #     'default': {
  #         'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
  #         'LOCATION': 'django_cache',
  #     }
  # }
  ```
* [x] Implement cache debugging tools:
  * [x] Detailed logging for cache hits/misses
  * [x] Cache verification on set
  * [x] API endpoint for testing cache functionality
* [x] Test the caching by:
  * [x] Making the same map request multiple times
  * [x] Verifying lower database query counts on cached requests
  * [x] Measuring performance improvements

### 4. Implement Progressive Detail Loading (3-4 hours) ✅

* [x] Add a new API endpoint in `checker/urls.py`:
  ```python
  # Add to urlpatterns
  path('api/component-map-detail/<int:component_id>/',
      views.component_map_detail_api, name='component_map_detail_api'),
  ```
* [x] Create the endpoint in `checker/views.py`:
  ```python
  @require_http_methods(["GET"])
  def component_map_detail_api(request, component_id):
      """API endpoint that returns detailed info for a specific component"""
      try:
          component = Component.objects.get(id=component_id)
          data = {
              'id': component.id,
              'title': component.location or 'Unknown Location',
              'technology': component.technology or 'Unknown',
              'display_technology': get_simplified_technology(component.technology),
              'company': component.company_name or 'Unknown',
              'description': component.description or '',
              'delivery_year': component.delivery_year or '',
              'cmu_id': component.cmu_id or '',
              'detailUrl': f'/component/{component.id}/'
          }
          return JsonResponse({'success': True, 'data': data})
      except Component.DoesNotExist:
          return JsonResponse({'success': False, 'error': 'Component not found'}, status=404)
  ```
* [x] Modify `map_data_api` to use detail levels:
  ```python
  # Add parameter
  detail_level = request.GET.get('detail_level', 'minimal')
  
  # Change .values() call based on detail level
  if detail_level == 'minimal':
      components_to_render = base_query.values(
          'id', 'latitude', 'longitude', 'technology', 'location'
      )[:limit]
  else:  # 'full'
      components_to_render = base_query.values(
          'id', 'latitude', 'longitude', 'technology', 'location',
          'company_name', 'description', 'delivery_year', 'cmu_id'
      )[:limit]
  ```
* [x] Update `map.html` to implement on-demand loading for marker details:
  * [x] Modify loadMarkers function to request minimal detail level by default
  * [x] Implement clientside caching of component details
  * [x] Create loadComponentDetails function for fetching additional details
  * [x] Update marker click handlers to use on-demand loading
  * [x] Create separate function for info window generation

### 5. Add Frontend Caching (1-2 hours) ✅

* [x] Implement comprehensive client-side caching in `map.html`:
  ```javascript
  // Add a cache object with management functions
  const mapDataCache = {};
  const CACHE_DURATION_MS = 5 * 60 * 1000; // 5 minutes
  
  // Cache check in loadMarkers function
  function loadMarkers(overrideTechnology = null) {
      // ... get parameters ...
      
      // Build a cache key from parameters
      const cacheKey = params.toString();
      
      // Try to get from cache
      if (mapDataCache[cacheKey] && mapDataCache[cacheKey].data) {
          const cachedItem = mapDataCache[cacheKey];
          const now = Date.now();
          
          // Check if cache is still valid
          if (now - cachedItem.timestamp < CACHE_DURATION_MS) {
              console.log(`%cCache HIT: Using cached data`, 'color: green; font-weight: bold');
              window.sessionStats.cacheHits++;
              
              // Use the cached data
              processMapData(cachedItem.data, 'cache');
              return;
          } else {
              // Remove expired entry
              delete mapDataCache[cacheKey];
          }
      }
      
      // ... fetch from API if not cached ...
      
      // Store in frontend cache
      mapDataCache[cacheKey] = {
          data: data,
          timestamp: Date.now(),
          size: JSON.stringify(data).length
      };
  }
  
  // Cache management function for limiting size
  function limitCacheSize(maxEntries = 20) {
      const cacheKeys = Object.keys(mapDataCache);
      if (cacheKeys.length > maxEntries) {
          // Sort keys by timestamp to find oldest entries
          const sortedKeys = cacheKeys.sort((a, b) => 
              (mapDataCache[a].timestamp || 0) - (mapDataCache[b].timestamp || 0)
          );
          
          // Remove oldest entries
          const keysToRemove = sortedKeys.slice(0, Math.ceil(sortedKeys.length * 0.2));
          keysToRemove.forEach(key => delete mapDataCache[key]);
      }
  }
  ```
* [x] Add statistics tracking and visualization for cache performance:
  ```javascript
  // Track usage stats
  window.sessionStats = {
      requestCount: 0,
      cachedRequestsCount: 0,
      totalDataSize: 0,
      cacheSizeBytes: 0,
      cacheHits: 0,
      cacheMisses: 0
  };
  
  // Update UI with cache stats
  function updateDataUsageUI() {
      const stats = window.sessionStats;
      const totalKB = (stats.totalDataSize / 1024).toFixed(1);
      const cacheSizeKB = ... // Calculate cache size
      
      statsElement.innerHTML = `
          <div>
              <strong>Data Usage:</strong> ${totalKB} KB
              <span><i class="bi bi-lightning-charge"></i> ${hitRate}% cache hit rate</span>
              Cache: ${cacheSizeKB} KB (${entryCount} entries)
          </div>
      `;
  }
  ```
* [x] Implement proper cache invalidation:
  * [x] Clear cache when filters change
  * [x] Remove expired entries automatically
  * [x] Limit cache size to prevent memory issues
* [x] Add debugging tools:
  * [x] Debug panel for examining cache contents
  * [x] Console logging with color formatting
  * [x] Cache hit/miss visualization

### 6. Monitor and Measure (Ongoing) 🔄 (Partially Complete)

* [x] Add frontend timing in `map.html`:
  ```javascript
  // At start of loadMarkers
  const startTime = performance.now();
  
  // After markers are rendered
  const endTime = performance.now();
  console.log(`Map rendering took ${(endTime - startTime).toFixed(2)}ms`);
  ```
* [x] Add performance tracking to `map_data_api`:
  ```python
  import time
  
  def map_data_api(request):
      start_time = time.time()
      
      # ... function body ...
      
      end_time = time.time()
      elapsed = end_time - start_time
      print(f"map_data_api took {elapsed:.2f} seconds (params: {request.GET})")
      
      # Return response
  ```

### Next Steps (Future Optimizations)

* [ ] **Production-Grade Caching**
  * [ ] Implement Redis caching for production using django-redis
  * [ ] Add more sophisticated cache key generation (e.g., rounding coordinates)
  * [ ] Implement cache warming for popular map regions and technologies
  * [ ] Add mechanism to selectively invalidate cache entries when data changes

* [ ] **Advanced Client-Side Caching**
  * [ ] Implement IndexedDB storage for persistent browser caching
  * [ ] Add offline support with Service Workers
  * [ ] Implement more aggressive client-side data pruning and aggregation for mobile devices
  * [ ] Add prefetching for adjacent map areas during idle periods

* [ ] **API and Performance Optimizations**
  * [ ] Improve Fuzzy Search Accuracy (Backend)
  * [ ] Implement Persistent Sorting for Search Results (Frontend/Backend)
  * [ ] Consider implementing server-side clustering for very large datasets
  * [ ] Refactor map JavaScript into proper classes/modules
  * [ ] Consider upgrading to Google Maps Advanced Markers API for better performance

* [ ] **Monitoring and Analytics**
  * [ ] Add server-side cache analytics (hits, misses, storage size)
  * [ ] Implement real-time performance monitoring
  * [ ] Add user-specific usage tracking (anonymized) to identify optimization targets
  * [ ] Create admin dashboard for cache and performance management

## Current Redis Usage Summary (May 2025)

After recent optimizations, Redis usage has been dramatically reduced:

**Still Using Redis:**
- CMU dataframe cache (~15MB) - justified for 1.4s performance gain
- Django cache backend for session/search result caching
- Map data caching (when implemented)

**Removed from Redis:**
- Location-to-postcode mappings (71.5GB → 3MB static JSON files)
- Company index (~5MB → direct PostgreSQL queries)

**Total Redis Usage:** <20MB (from original 71.5GB+)

## Current Focus / Next Steps

### Location Search Performance Analysis (May 2025)

Location search is now the primary performance bottleneck (2-5s). See LOCATION_SEARCH_OPTIMIZATION.md for detailed analysis and implementation plan.

Main issues:

1. **Component Filtering for Location Matching**:
   - Current approach queries Component model to find matching locations
   - Then queries LocationGroup model with those locations
   - This creates a two-step process that could be optimized
   
2. **JSON Field Queries**:
   - Although GIN indexes are added, complex JSON queries can still be slow
   - Consider denormalizing frequently searched fields
   - May need to add functional indexes on specific JSON paths
   
3. **Postcode Expansion**:
   - Still relies on in-memory postcode mappings
   - Consider moving postcode data to database for better query integration
   
4. **Location Detail View**:
   - Fetches all components for a location on detail page
   - Could benefit from pagination or lazy loading
   - CMU Registry lookups could be optimized with prefetch_related

### Recommended Optimizations:

1. **Direct LocationGroup Search**:
   - Add full-text search capability directly to LocationGroup
   - Create computed search_vector field combining location, companies, technologies
   - This would eliminate the need to query Component model first
   
2. **Materialized Views**:
   - Consider PostgreSQL materialized views for complex aggregations
   - Could pre-compute common search patterns
   
3. **Database-level Postcode Mapping**:
   - Create PostcodeMapping model to store postcode relationships
   - Enable direct SQL joins instead of Python-level expansion
   
4. **Optimize JSON Queries**:
   - Use PostgreSQL's jsonb operators more efficiently
   - Consider functional indexes like: `CREATE INDEX ON locationgroup ((companies->>'CompanyName'))`
   
5. **Component Detail Prefetching**:
   - Use select_related/prefetch_related for CMURegistry lookups
   - Implement pagination for locations with many components

- **Performance Tuning (SQL):** Analyze slow queries identified by Django Debug Toolbar (esp. for location/company searches) and optimize.
- **Refactor `search_components_service`:** Break down the monolithic function in `company_search.py` into smaller, focused functions (e.g., analyze query intent, find candidate companies, build component filters, execute search/pagination).
- **Improve Query Intent Analysis:** Enhance logic to better determine if a search term is a CMU ID, location, company name, or general term.
- **Refine Company Link Generation:** Improve the logic for finding and scoring company candidates for the "Matching Companies" section to enhance relevance (e.g., adjust fuzzy matching, filter by intent).

## Medium-Priority Optimizations

### 1. Static File Compression & Caching Headers (Frontend/Deployment)

**Files to Examine:**
- `capacity_checker/settings.py` - `MIDDLEWARE` (WhiteNoise)
- `Procfile` / deployment scripts (if applicable)

**Findings:**
- `whitenoise.middleware.WhiteNoiseMiddleware` is present, which handles static file serving and compression (if brotli/gzip libs are installed).
- `CompressedManifestStaticFilesStorage` is used, which helps with caching via hashed filenames.

**Recommended Actions:**
- Ensure compression libraries (`brotli`, `gzip`) are installed in the production environment.
- Verify HTTP Cache-Control headers are being set correctly by WhiteNoise for static assets (usually immutable for hashed files).
- Consider using a CDN for static assets to further improve load times and reduce egress from the main server.

**Expected Impact:** Medium
- Faster initial page loads due to smaller static files.
- Reduced server load as browsers cache static assets effectively.

### 2. Client-Side Filtering/Refinement (Frontend)

**Files to Examine:**
- `checker/templates/checker/map.html` - JavaScript related to markers and filters

**Findings:**
- Currently, all filtering happens on the backend via API calls.

**Recommended Actions:**
- For certain scenarios (e.g., when only a few thousand markers are loaded for a specific technology), consider adding client-side controls to further filter markers *already loaded* in the browser based on:
    - Sub-technology types (if applicable)
    - Company name (if included in minimal data)
    - Year ranges (if included in minimal data)
- This would provide instant filtering without needing new backend requests.

**Expected Impact:** Low-Medium
- Improved user experience for fine-tuning results without waiting for API.
- Might slightly increase initial data load if more fields are needed for client-side filtering.

## Low-Priority Optimizations

### 1. JavaScript Code Splitting / Lazy Loading (Frontend)

**Files to Examine:**
- `checker/templates/checker/map.html` - JavaScript includes
- Potentially requires a build step (e.g., Webpack, Parcel)

**Findings:**
- JavaScript is likely loaded all at once.

**Recommended Actions:**
- If the JS codebase grows significantly, implement code splitting to only load necessary JS bundles for the current view.
- Lazy-load non-critical JS (e.g., analytics, less common map interactions).

**Expected Impact:** Low (unless JS size becomes very large)
- Slightly faster initial script parsing and execution.

### 2. HTML Minification (Deployment)

**Files to Examine:**
- Deployment process / potential middleware

**Findings:**
- HTML is likely not minified.

**Recommended Actions:**
- Implement HTML minification during deployment or via middleware (e.g., `django-htmlmin`).

**Expected Impact:** Low
- Minor reduction in HTML payload size.

## General Cleanup / Maintenance

- Clean up unused `capacity_checker` directory/files (settings.py, wsgi.py) if confirmed they are redundant after switching to `cmr` structure. 

## Account Page & Payment Integration (New Feature - May 2024)

**Goal:** Create an account page where logged-in users can see details, change password, and are subject to a usage timer. If the timer expires, they are prompted to pay via Stripe for continued access.

**Prerequisites:**
- Stripe Product/Price ID for paid access.
- Stripe Webhook Endpoint configured for `checkout.session.completed`.
- Stripe Webhook Signing Secret.

**Plan:**

1.  **[ ] Create `UserProfile` Model (`accounts/models.py`):**
    *   Fields: `user` (OneToOneField to `User`), `has_paid_access` (BooleanField, default=False), `paid_access_expiry_date` (DateTimeField, nullable=True).
    *   Run `makemigrations accounts` and `migrate`.
    *   **(Optional)** Implement `post_save` signal to auto-create profile for new users.

2.  **[ ] Create Account View (`accounts/views.py`) and URL (`accounts/urls.py`):**
    *   `account_view` function, protected with `@login_required`.
    *   Fetches `request.user` and related `UserProfile`.
    *   Passes user details and `has_paid_access` to context.
    *   Add URL pattern (e.g., `/account/`) pointing to `account_view`.

3.  **[ ] Create Account Template (`accounts/templates/accounts/account.html`):**
    *   Extend `checker/base.html`.
    *   Display `{{ user.username }}`, `{{ user.email }}`.
    *   Link to `{% url 'password_change' %}`.
    *   Add `<div id="access-timer"></div>` for countdown.
    *   Include `<script>` block for timer logic.

4.  **[ ] Implement Timer JavaScript (in `account.html`):**
    *   Get `has_paid_access` from context (use `json_script`).
    *   If `has_paid_access` is true, display "Full access active."
    *   If false:
        *   Define total allowed time (e.g., 3600 seconds).
        *   Use `sessionStorage` to track `loginTimestamp` (or similar start time).
        *   Calculate remaining time.
        *   If remaining <= 0, redirect to payment page URL.
        *   If remaining > 0:
            *   Display countdown in `#access-timer`.
            *   Use `setInterval` to update display.
            *   Use `setTimeout` for the full duration to redirect on expiry.

5.  **[ ] Create Payment View (`accounts/views.py`) and Template (`accounts/templates/accounts/payment.html`):**
    *   `initiate_payment_view` function, protected with `@login_required`.
    *   Template explains need to pay.
    *   View initiates Stripe Checkout session (using paid access Price ID).
    *   Store `user.id` in Checkout `metadata`.
    *   Redirect to Stripe.
    *   Define `success_url` and `cancel_url`.

6.  **[ ] Create Stripe Webhook Handler (`accounts/views.py`):**
    *   `stripe_webhook_view` function, CSRF exempt (`@csrf_exempt`).
    *   Listen for `checkout.session.completed` event.
    *   Verify webhook signature (use Signing Secret).
    *   If valid and payment succeeded:
        *   Retrieve `user.id` from session metadata.
        *   Find `UserProfile`, update `has_paid_access = True` (and optionally expiry date).

7.  **[ ] Password Change Templates:**
    *   Ensure Django's built-in password change templates exist and are styled (`registration/password_change_form.html`, `password_change_done.html`).

8.  **[ ] Ensure Login/Logout Redirects:**
    *   Set `LOGIN_REDIRECT_URL` (e.g., to `/account/`) and `LOGOUT_REDIRECT_URL` (e.g., to `/`) in `settings.py`.

9.  **[ ] Add Link to Account Page:**
    *   Add a link to the new `/account/` page in the `base.html` navigation for logged-in users. 