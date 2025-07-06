# "View on Map" Implementation Plan

## Core Approach

The implementation follows these principles:
1. When search results are < 200, show a "View on Map" button
2. Button takes user to map view with the same search results
3. Existing search results are converted to GeoJSON for the map

## Implementation Steps

### 1. Add "View on Map" Button to Search Results

Update the search results template to include a "View on Map" button when appropriate:

```html
<!-- In search_results.html -->
<div class="search-controls mb-3">
    <div class="d-flex justify-content-between align-items-center">
        <h2>Search Results for "{{ search_query }}"</h2>
        
        {% if total_results < 200 and total_results > 0 %}
            <a href="/map_search/?q={{ search_query|urlencode }}" class="btn btn-primary">
                <i class="bi bi-map"></i> View on Map
            </a>
        {% endif %}
    </div>
    <div class="text-muted">{{ total_results }} results found</div>
</div>
```

### 2. Create a Simplified Map View

The map view doesn't do its own search - it just displays results from the main search:

```python
# In views.py
def map_search_view(request):
    """Display search results on a map."""
    search_query = request.GET.get('q', '')
    
    if not search_query:
        # No query provided, redirect to main search
        return redirect('/')
    
    # We'll use the search query in the template and let JavaScript
    # fetch the actual GeoJSON data
    context = {
        'search_query': search_query,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'is_search_view': True,
    }
    
    return render(request, 'checker/map_search.html', context)
```

### 3. Add GeoJSON API Endpoint for Search Results

Create a dedicated endpoint that returns search results as GeoJSON:

```python
# In views.py
def search_results_geojson(request):
    """Return search results as GeoJSON for map display."""
    search_query = request.GET.get('q', '')
    
    if not search_query:
        # Return empty result set if no query
        empty_response = {
            'type': 'FeatureCollection',
            'features': [],
            'metadata': {'count': 0, 'total': 0}
        }
        return JsonResponse(empty_response)
    
    # Use the existing search function to get results
    # This ensures consistency with the list view
    search_results = perform_component_search(search_query)
    
    # Convert to GeoJSON
    features = []
    geocoded_count = 0
    non_geocoded_count = 0
    
    for component in search_results:
        if component.latitude and component.longitude:
            geocoded_count += 1
            
            # Create a GeoJSON feature
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [component.longitude, component.latitude]
                },
                'properties': {
                    'id': component.id,
                    'title': component.location or 'Unknown Location',
                    'technology': component.technology or 'Unknown',
                    'company': component.company_name or 'Unknown',
                    'description': component.description or '',
                    'cmu_id': component.cmu_id,
                    'delivery_year': component.delivery_year or '',
                    'detailUrl': f'/component/{component.id}/'
                }
            }
            features.append(feature)
        else:
            non_geocoded_count += 1
    
    # Create the GeoJSON response
    response_data = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'count': len(features),
            'total': len(search_results),
            'geocoded_count': geocoded_count,
            'non_geocoded_count': non_geocoded_count,
            'query': search_query
        }
    }
    
    return JsonResponse(response_data)
```

### 4. Update Map JavaScript to Load and Display GeoJSON

Simplify the map view JavaScript to fetch and display the GeoJSON:

```javascript
// In map_search.html
function loadMapResults() {
    const searchQuery = document.getElementById('search-query-input').value;
    
    // Show loading
    showStatus("Loading map data...");
    document.getElementById('loading-overlay').style.display = 'flex';
    
    // Clear existing markers
    clearMarkers();
    
    // Fetch GeoJSON from our search API
    fetch(`/api/search-geojson/?q=${encodeURIComponent(searchQuery)}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(`Received ${data.features.length} features (from ${data.metadata.total} results)`);
            
            // Update search info
            document.getElementById('result-count').textContent = data.metadata.count;
            document.getElementById('search-query').textContent = data.metadata.query;
            
            // Process the features
            processMapData(data);
        })
        .catch(error => {
            console.error("Error loading map data:", error);
            showStatus(`Error: ${error.message}`, 3000);
        })
        .finally(() => {
            document.getElementById('loading-overlay').style.display = 'none';
        });
}
```

### 5. Add URL Route for the GeoJSON Endpoint

Add the new endpoint to `urls.py`:

```python
# In urls.py
urlpatterns = [
    # Existing routes...
    
    # New search_geojson endpoint
    path('api/search-geojson/', views.search_results_geojson, name='search_results_geojson'),
    
    # Existing map routes...
]
```

## Future Enhancement: Technology-Based Markers

For the next phase, we'll add technology-based styling to markers:

```javascript
function createMarker(feature) {
    const position = { 
        lat: feature.geometry.coordinates[1], 
        lng: feature.geometry.coordinates[0]
    };
    
    // Get technology type for styling
    const techType = feature.properties.technology || 'Unknown';
    
    // Technology color mapping
    const techColors = {
        'OCGT': '#F44336',  // Red
        'Wind': '#4CAF50',  // Green
        'Solar': '#FFC107',  // Amber
        'DSR': '#2196F3',    // Blue
        'Battery': '#9C27B0',  // Purple
        'Nuclear': '#FF9800',  // Orange
        // Add more technology mappings
        'Unknown': '#607D8B'  // Grey
    };
    
    // Get color based on technology
    const techColor = techColors[techType] || techColors['Unknown'];
    
    // Create styled marker element
    const markerElement = document.createElement('div');
    markerElement.className = 'tech-marker';
    markerElement.style.width = '30px';
    markerElement.style.height = '30px';
    markerElement.style.backgroundColor = techColor;
    markerElement.style.borderRadius = '50%';
    markerElement.style.border = '2.5px solid white';
    markerElement.style.boxShadow = '0 1px 2px rgba(0,0,0,0.3)';
    
    // Create advanced marker
    const marker = new google.maps.marker.AdvancedMarkerElement({
        position: position,
        content: markerElement,
        title: feature.properties.title || 'Component'
    });
    
    // Add info window click handler
    // ...
    
    return marker;
}
```

## Advantages of This Approach

1. **Uses Existing Search Logic**: Leverages the same search implementation that powers the list view
2. **Simple User Flow**: Natural progression from list results to map visualization
3. **Performance Control**: Only shows map button when results are manageable (< 200)
4. **Maintainable**: Single source of truth for search results
5. **Progressive Enhancement**: Can easily add technology styling as a separate improvement

## Implementation Priorities

1. First implement the basic "View on Map" button and GeoJSON endpoint
2. Verify it works with the SW11 search case
3. Add technology-based marker styling as a follow-up enhancement

This approach is focused, clean, and builds directly on your existing search functionality without duplication.