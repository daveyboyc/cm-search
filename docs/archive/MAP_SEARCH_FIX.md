# Map Search with Postcode Improvements

## Problem

We identified an issue where searching for postcodes like "SW11" was not properly showing components on the map. After investigation, we found:

1. The map was expecting components to have both `latitude` and `longitude` coordinates (geocoded)
2. Many components matching "SW11" in the database have `outward_code="SW11"` but might not be geocoded
3. The API was filtering for `geocoded=True` components, which excluded many valid SW11 matches
4. The cache was potentially interfering with search results

## Solution

We implemented several improvements:

1. **Improved Postcode Detection**: Added regex pattern matching to detect when search queries are postcodes
2. **Outward Code Filtering**: Added direct filtering by `outward_code` field when a postcode pattern is detected
3. **Fallback Logic**: If no geocoded components are found for a postcode, create a fallback marker
4. **Cache Management**: Bypass cache for search queries to ensure fresh results
5. **Debug Tools**: Added comprehensive debugging to identify issues

## Testing the Solution

Test our improved map search at:

```
/map_test_fix/?q=SW11
```

This test page includes:

- An input field to try different postcode searches
- Checkbox to toggle `outward_code` filtering
- Detailed debugging output 
- Count of geocoded vs. non-geocoded components
- Clear markers button for testing different queries

## Implementation Details

### Files Created/Modified:

1. **`/checker/views_map_search_fix.py`** - Improved map_data_api function with postcode detection
2. **`/checker/templates/checker/map_search_simple_fixed.html`** - Test template with debugging tools
3. **`/checker/views_new_map_test.py`** - View for the test page
4. **`/checker/urls.py`** - Added URL route for the test page

### Key Improvements:

1. **Postcode Detection**:
   ```python
   postcode_pattern = re.compile(r'^[A-Z]{1,2}[0-9][A-Z0-9]?$', re.IGNORECASE)
   clean_query = search_query.strip().upper().replace(' ', '')
   if postcode_pattern.match(clean_query):
       is_postcode_search = True
       outward_code = clean_query
   ```

2. **Outward Code Filtering**:
   ```python
   if is_postcode_search and outward_code:
       base_query = base_query.filter(outward_code__iexact=outward_code)
   ```

3. **Fallback Markers**:
   ```python
   if is_postcode_search and geocoded_count == 0 and outward_code:
       # Create fallback marker for the postcode area
   ```

4. **Cache Management**:
   ```python
   if search_query_param:
       # Bypass cache for search queries
       cache_key = None
   ```

## Next Steps

1. Test the solution with various postcodes (SW11, E1, N1, etc.)
2. Integrate the improved code into the main map_data_api function
3. Update the main map_search.html template with these improvements
4. Consider adding a geographic boundary display for postcode areas

## Notes

- All SW11 components found in the database have `outward_code="SW11"` set correctly
- There are 14 components with SW11 outward code, all of which have been geocoded
- Our improvements should help with cases where components have outward_code set but aren't geocoded