# Comprehensive Map Search Enhancement Plan

## 1. Core Issues Identified

The SW11 fix revealed several underlying issues in the map search implementation:

1. **Limited Postcode Search Support**: The system doesn't properly recognize and handle postcode-based searches.
2. **Inconsistent Filtering Logic**: Different filters (technology, company, search) interact in unpredictable ways.
3. **Over-aggressive Filtering**: Multiple filtering stages can lead to zero results when each filter is too strict.
4. **Cache Management Issues**: Stale cache entries prevent updated logic from taking effect.
5. **Visualization Limitations**: Current marker implementation doesn't fully utilize Google Maps' Advanced Markers.

## 2. Sustainable Solution Architecture

### A. Improved Search Query Analysis

Create a preprocessing layer that analyzes search queries before filtering:

```python
def analyze_search_query(query):
    """Analyze search query to determine most appropriate search strategy."""
    result = {
        'raw_query': query,
        'is_postcode': False,
        'outward_code': None,
        'is_technology': False,
        'is_company': False,
        'search_terms': []
    }
    
    # Check for postcode pattern
    postcode_pattern = re.compile(r'^[A-Z]{1,2}[0-9][A-Z0-9]?$', re.IGNORECASE)
    clean_query = query.strip().upper().replace(' ', '')
    if postcode_pattern.match(clean_query):
        result['is_postcode'] = True
        result['outward_code'] = clean_query
    
    # Check if query matches known technology types
    tech_list = get_all_technology_types()
    if query.lower() in [t.lower() for t in tech_list]:
        result['is_technology'] = True
    
    # Check if query matches a company name
    company_list = get_all_company_names()
    if query.lower() in [c.lower() for c in company_list]:
        result['is_company'] = True
    
    # Process search terms for general text search
    result['search_terms'] = query.lower().split()
    
    return result
```

### B. Staged Filtering with Fallbacks

Implement a staged filtering approach that applies filters progressively and falls back if results are too few:

```python
def staged_filtering(base_query, search_analysis, min_results=10):
    """Apply filters in stages, with fallbacks if results are too few."""
    results = base_query
    
    # Stage 1: Apply the most specific filter based on query analysis
    if search_analysis['is_postcode']:
        postcode_results = base_query.filter(outward_code__iexact=search_analysis['outward_code'])
        if postcode_results.count() >= min_results:
            results = postcode_results
            return results, 'postcode_exact'
    
    # Stage 2: Try location-based text search
    location_results = base_query.filter(
        Q(location__icontains=search_analysis['raw_query'])
    )
    if location_results.count() >= min_results:
        results = location_results
        return results, 'location_match'
    
    # Stage 3: Apply general text search across all fields
    general_results = apply_text_search(base_query, search_analysis['search_terms'])
    if general_results.count() >= min_results:
        results = general_results
        return results, 'general_search'
    
    # If we still have too few results, return everything we have
    all_results = postcode_results | location_results | general_results
    return all_results.distinct(), 'combined_search'
```

### C. Smart Technology Filtering

Implement technology filtering that works cooperatively with search queries:

```python
def smart_technology_filter(query, requested_tech, search_query=None):
    """Apply technology filtering with awareness of search context."""
    
    # If we have both a search query and technology filter, handle specially
    if search_query and requested_tech and requested_tech != 'All':
        # First get all search results
        search_results = apply_search_filter(query, search_query)
        tech_count = search_results.filter(technology=requested_tech).count()
        
        # If tech filter would leave reasonable number of results, apply it
        if tech_count >= 5:
            return search_results.filter(technology=requested_tech), True
        else:
            # Otherwise, keep all search results but prioritize the requested tech
            return search_results, False
    
    # Regular technology filtering
    if not requested_tech or requested_tech == 'All':
        return query, False
    
    return query.filter(technology=requested_tech), True
```

### D. Enhanced Marker Visualization

Develop an improved marker visualization system using Google's Advanced Markers:

```javascript
function createAdvancedMarker(feature) {
    const position = {
        lat: feature.geometry.coordinates[1],
        lng: feature.geometry.coordinates[0]
    };
    
    // Get technology type for styling
    const techType = feature.properties.display_technology || 'Unknown';
    
    // Define color based on technology
    const techColors = {
        'Wind': '#4CAF50',
        'Solar': '#FFC107',
        'Gas': '#F44336',
        'DSR': '#2196F3',
        'Battery': '#9C27B0',
        // Add more technology types and colors
        'Unknown': '#607D8B'
    };
    
    const color = techColors[techType] || techColors['Unknown'];
    
    // Create custom element for marker
    const markerElement = document.createElement('div');
    markerElement.className = 'advanced-marker';
    markerElement.dataset.technology = techType;
    
    // Style the marker
    markerElement.style.width = '30px';
    markerElement.style.height = '30px';
    markerElement.style.backgroundColor = color;
    markerElement.style.borderRadius = '50%';
    markerElement.style.border = '2.5px solid white';
    markerElement.style.boxShadow = '0 1px 2px rgba(0,0,0,0.3)';
    
    // Add technology icon if available
    const iconElement = document.createElement('span');
    iconElement.className = `tech-icon tech-${techType.toLowerCase().replace(/\s+/g, '-')}`;
    markerElement.appendChild(iconElement);
    
    // Create the Advanced Marker
    const marker = new google.maps.marker.AdvancedMarkerElement({
        position: position,
        content: markerElement,
        title: feature.properties.title || ''
    });
    
    // Add info window and click handlers
    // ...
    
    return marker;
}
```

### E. Improved Cache Management

Implement a smarter cache management system:

```python
def get_map_cache_key(request_params, cache_segment=15):
    """
    Generate appropriate cache key based on request parameters.
    cache_segment determines how often the cache key changes (in minutes).
    """
    search_query = request_params.get('q', '') or request_params.get('search_query', '')
    
    # For search queries, use time-segmented cache to avoid staleness
    if search_query:
        import time
        # Cache key changes every {cache_segment} minutes for search queries
        time_segment = int(time.time() / (cache_segment * 60))
        search_hash = hashlib.md5(search_query.lower().encode('utf-8')).hexdigest()[:8]
        return f"map_search_{search_hash}_{time_segment}"
    
    # For non-search queries, use parameter-based caching
    relevant_params = [
        'technology', 'company', 'year', 'detail_level', 
        'exact_technology', 'cm_period'
    ]
    filtered_params = {k: request_params.get(k, '') 
                      for k in relevant_params if k in request_params}
    
    # Add viewport parameters only if all are present
    viewport_params = ['north', 'south', 'east', 'west']
    if all(p in request_params for p in viewport_params):
        for p in viewport_params:
            filtered_params[p] = request_params.get(p, '')
    
    # Create deterministic parameter string
    param_string = json.dumps(sorted(filtered_params.items()))
    param_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    
    return f"map_data_{param_hash}"
```

## 3. Implementation Roadmap

### Phase 1: Search and Filtering Improvements

1. **Implement Query Analysis System**:
   - Create preprocessing for all search queries
   - Add detection for postcodes, technologies, and companies
   - Develop test suite for query analysis accuracy

2. **Build Staged Filtering Framework**:
   - Implement progressive filtering with fallbacks
   - Add monitoring for filter effectiveness
   - Create configurable filtering thresholds

3. **Design New Cache Management System**:
   - Implement time-segmented cache for search queries
   - Create cache key generation based on query type
   - Add cache control endpoint for admin users

### Phase 2: Visualization Enhancements

1. **Upgrade to Advanced Markers**:
   - Implement technology-based styling
   - Add technology icons to markers
   - Create custom marker elements

2. **Improve Marker Clustering**:
   - Implement custom clustering for Advanced Markers
   - Add cluster splitting on zoom
   - Create technology-aware cluster visualization

3. **Add Technology Legend and Filtering**:
   - Create interactive technology filter UI
   - Implement client-side filtering for quick response
   - Design color-coded technology legend

### Phase 3: UI and Performance Improvements

1. **Create Enhanced Search UI**:
   - Add postcode search suggestions
   - Implement technology type-ahead
   - Design clear search results indicators

2. **Implement Viewport Management**:
   - Create smart viewport adjustment for search results
   - Add "show all" viewport option
   - Implement progressive loading based on viewport

3. **Add Performance Monitoring**:
   - Create timing metrics for all filtering stages
   - Implement monitoring for cache effectiveness
   - Add performance dashboard for admins

## 4. Technical Implementation Details

### Postcode Detection and Handling

```python
def is_postcode(query):
    # Full UK postcode regex (both outward and inward codes)
    full_pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$'
    # Outward code only regex
    outward_pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]?$'
    
    clean = query.strip().upper().replace(' ', '')
    
    if re.match(full_pattern, clean):
        # Extract outward code from full postcode
        outward = re.match(r'^([A-Z]{1,2}[0-9][A-Z0-9]?)', clean).group(1)
        return True, outward
    elif re.match(outward_pattern, clean):
        return True, clean
    
    return False, None
```

### Dynamic Filtering Logic

```python
def build_query_with_filters(base_query, params, min_results=10):
    """Build query applying filters dynamically based on params."""
    
    search_query = params.get('q', '') or params.get('search_query', '')
    tech_filter = params.get('technology', '')
    company_filter = params.get('company', '')
    year_filter = params.get('year', '')
    
    # Start with all components (no filtering)
    query = base_query
    applied_filters = []
    
    # First apply search query if present
    if search_query:
        is_postcode, outward_code = is_postcode(search_query)
        
        if is_postcode and outward_code:
            # Try outward code filter first
            postcode_query = query.filter(outward_code__iexact=outward_code)
            if postcode_query.count() >= min_results:
                query = postcode_query
                applied_filters.append(f"postcode:{outward_code}")
            else:
                # Fall back to location search
                location_query = query.filter(location__icontains=search_query)
                if location_query.count() >= min_results:
                    query = location_query
                    applied_filters.append(f"location:{search_query}")
                else:
                    # Fall back to general text search
                    text_query = apply_text_search(query, search_query)
                    query = text_query
                    applied_filters.append(f"text:{search_query}")
        else:
            # Regular search query
            query = apply_text_search(query, search_query)
            applied_filters.append(f"text:{search_query}")
    
    # Apply technology filter if present
    if tech_filter and tech_filter != 'All':
        # Check if filter would eliminate too many results
        tech_count = query.filter(technology=tech_filter).count()
        if tech_count >= min_results or not applied_filters:  # Apply unless it leaves too few results
            query = query.filter(technology=tech_filter)
            applied_filters.append(f"tech:{tech_filter}")
    
    # Similarly apply other filters only if they don't eliminate too many results
    # ...
    
    return query, applied_filters
```

### Advanced Marker Clustering System

```javascript
class TechnologyAwareClusterer {
    constructor(map) {
        this.map = map;
        this.markers = [];
        this.clusters = [];
        this.gridSize = 60;
        this.maxZoom = 15;
    }
    
    addMarkers(markers) {
        this.markers = markers;
        this.cluster();
    }
    
    clearMarkers() {
        this.markers.forEach(marker => marker.map = null);
        this.markers = [];
        this.clusters.forEach(cluster => cluster.marker.map = null);
        this.clusters = [];
    }
    
    cluster() {
        // Clear existing clusters
        this.clusters.forEach(cluster => cluster.marker.map = null);
        this.clusters = [];
        
        if (!this.markers.length) return;
        
        const zoom = this.map.getZoom();
        
        // If zoomed in beyond maxZoom, show all markers
        if (zoom >= this.maxZoom) {
            this.markers.forEach(marker => marker.map = this.map);
            return;
        }
        
        // Group markers by grid cells, keeping technology types separate
        const techClusters = {};
        
        this.markers.forEach(marker => {
            const position = marker.position;
            const pixel = this.map.getProjection().fromLatLngToPoint(position);
            const gridX = Math.floor(pixel.x * Math.pow(2, zoom) / this.gridSize);
            const gridY = Math.floor(pixel.y * Math.pow(2, zoom) / this.gridSize);
            
            // Extract technology from marker content
            const tech = marker.content.dataset.technology || 'Unknown';
            
            const gridKey = `${gridX}_${gridY}`;
            const key = `${gridKey}_${tech}`;
            
            if (!techClusters[key]) {
                techClusters[key] = {
                    position: position,
                    markers: [],
                    technology: tech
                };
            }
            
            techClusters[key].markers.push(marker);
        });
        
        // Create cluster markers
        Object.values(techClusters).forEach(cluster => {
            if (cluster.markers.length === 1) {
                // Just show the single marker
                cluster.markers[0].map = this.map;
            } else {
                // Create cluster marker
                this.createClusterMarker(cluster);
            }
        });
    }
    
    createClusterMarker(cluster) {
        // Implementation for creating tech-specific cluster markers
        // ...
    }
}
```

## 5. Benefits and Success Metrics

### Benefits

1. **Improved Search Relevance**: Different search types will be handled appropriately.
2. **More Reliable Results**: Staged filtering ensures users always see relevant results.
3. **Better Visualization**: Technology-based markers provide clearer information.
4. **Faster Performance**: Improved caching and client-side filtering reduce server load.
5. **Enhanced User Experience**: Clear visual indicators and intuitive filtering improve usability.

### Success Metrics

1. **Search Result Count**: Increase in non-zero result searches.
2. **User Engagement**: Longer time spent on map view, more marker interactions.
3. **Cache Performance**: Higher cache hit rate, reduced API response time.
4. **Filter Usage**: Increased use of technology and other filters.
5. **Zero-Result Rate**: Reduction in searches that return no results.

## 6. Testing and Quality Assurance

1. **Unit Tests**:
   - Search query analysis for different query types
   - Filtering logic with various parameter combinations
   - Cache key generation for different scenarios

2. **Integration Tests**:
   - End-to-end tests for search-to-marker flow
   - Cache invalidation and refreshing
   - Technology filtering across different search types

3. **Performance Tests**:
   - Load testing with large result sets
   - Cache hit/miss ratio monitoring
   - Client-side rendering performance

4. **User Acceptance Testing**:
   - Test with common search scenarios
   - Validate marker visibility and clustering
   - Verify technology filtering accuracy

This comprehensive plan provides a sustainable approach to the map search functionality that will handle all types of searches, not just postcodes, while enhancing the visual experience with technology-based Advanced Markers. The staged implementation allows for incremental improvements while maintaining working functionality throughout the process.