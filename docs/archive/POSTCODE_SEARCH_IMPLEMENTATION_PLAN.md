# Postcode Map Search Implementation Plan

## Summary of Issue

Our investigation found that the map search was not properly displaying components matching postcode searches like "SW11". The core issues were:

1. The map API was filtering for `geocoded=True` components for all searches
2. Postcode searches should filter by `outward_code` field, not just text matching
3. The caching system was potentially interfering with search results
4. The map search interface had limited debugging tools

## Implementation Plan

### Phase 1: Integrate Improved Postcode Search Logic

1. **Update map_data_api Function**:
   - Add postcode pattern detection using regex
   - Implement outward_code filtering for postcode searches
   - Add fallback marker creation for ungeocoded postcode areas
   - Skip cache for search queries to ensure fresh results
   - Add improved debugging output

2. **Update map_search.html Template**:
   - Add clear display of search query results
   - Show count of geocoded vs. non-geocoded components
   - Add reset button and clear markers functionality

### Phase 2: Add Testing and Monitoring

1. **Keep the Test Interface**:
   - Leave `/map_test_fix/` route accessible for testing
   - Use it to compare behavior with the main implementation

2. **Add Logging**:
   - Add log entries for postcode search detection
   - Track count of components found by outward_code vs. text search
   - Monitor fallback marker usage

### Phase 3: Extend Functionality

1. **Add Postcode Area Visualization**:
   - Consider adding geographic boundary for the postcode area
   - Show area even when specific components aren't found

2. **Improve Postcode Data**:
   - Ensure all components have correct outward_code values
   - Consider adding full postcode validation and parsing

3. **Enhance UI for Postcode Searches**:
   - Add special icon for postcode search results
   - Consider adding postcode-specific filtering options

## Technical Implementation Details

### 1. Postcode Detection Function

```python
def is_outward_code(query):
    """Check if a search query is a UK outward code."""
    import re
    # Pattern for UK outward codes (e.g., SW11, E1, W1A)
    pattern = re.compile(r'^[A-Z]{1,2}[0-9][A-Z0-9]?$', re.IGNORECASE)
    clean_query = query.strip().upper().replace(' ', '')
    return pattern.match(clean_query) is not None, clean_query
```

### 2. Modified Filtering Logic

```python
search_query = request.GET.get('q', '') or request.GET.get('search_query', '')
is_postcode, clean_postcode = is_outward_code(search_query)

if is_postcode:
    # Try outward_code filtering first
    components = Component.objects.filter(outward_code__iexact=clean_postcode)
    postcode_count = components.count()
    
    if postcode_count > 0:
        return components
    else:
        # Fall back to text search
        return standard_text_search(search_query)
else:
    # Standard search logic
    return standard_text_search(search_query)
```

### 3. Fallback Marker Generation

```python
if is_postcode and geocoded_count == 0:
    # Add fallback marker for the postcode area
    fallback_coords = get_postcode_center(clean_postcode)
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [fallback_coords['lng'], fallback_coords['lat']]
        },
        'properties': {
            'id': 0,
            'title': f'{clean_postcode} Area',
            'is_fallback': True,
            # Other properties...
        }
    })
```

## Testing and Verification Steps

1. Test with known postcode patterns:
   - Full postcodes: "SW11 1AB"
   - Outward codes only: "SW11", "E1", "W1A"
   - Variations with spaces: "S W 1 1"
   - Mixed case: "sW11"

2. Test with components that have:
   - Both outward_code and geocoding
   - outward_code but no geocoding
   - geocoding but no outward_code

3. Verify display for:
   - Multiple components with same postcode
   - Single component with unique postcode
   - No components matching postcode

## Integration with Existing Code

Since the map functionality is complex and critical, we recommend:

1. Make the changes in a dedicated feature branch
2. Keep the test implementation at `/map_test_fix/` during development
3. Implement changes gradually, starting with the core postcode detection
4. Add comprehensive logging to help diagnose issues
5. Use Django DEBUG setting to enable detailed logging in development

## Conclusion

The improved postcode search functionality will make the map much more useful for location-based searches. By implementing proper outward_code filtering, we'll ensure users can find components by postcode area even when components don't have precise geocoding information.

The key insight from our investigation is that we need to treat postcode searches as a special case with dedicated filtering logic - not just as regular text searches. This approach aligns with user expectations when searching by postcode.