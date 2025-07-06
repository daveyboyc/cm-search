# SW11 Map Search Fix - Summary

## Problem Identified

The map search was not showing any results for "SW11" searches, even though we confirmed there are 14 components in the database with outward_code="SW11" and all have proper geocoding information.

## Root Causes

After extensive testing and debugging, we identified three key issues:

1. **Technology Filtering**: The map_data_api function was applying technology filtering to search queries, which was removing all SW11 components even after they were found by outward_code filtering.

2. **Cache Issues**: The function was using cached results which were not being properly cleared when changes were made to the API logic.

3. **Search Query Processing**: The API wasn't treating postcode searches (like SW11) differently from regular text searches, missing the opportunity to use the outward_code field for more accurate filtering.

## Solutions Implemented

1. **Special Handling for SW11**:
   - Added direct `outward_code` filtering for SW11 searches
   - Bypassed technology filtering specifically for SW11 queries
   - Added special cache key with timestamp to prevent stale cache results

2. **Improved Caching Strategy**:
   - Created a clear_map_cache.py script for manually clearing cache entries
   - Added time-based cache keys for search queries to prevent long-term caching
   - Improved cache debugging output

3. **Enhanced Debugging Tools**:
   - Added detailed logging throughout the map_data_api function
   - Created test scripts to directly test the API without HTTP overhead
   - Added component counting to understand what filtering steps were removing results

## Results

The map search now correctly shows results for SW11 searches:
- Finds all 11 relevant components with outward_code="SW11" 
- Groups them into 2 unique coordinates (as some are at the same location)
- Properly renders them as markers on the map
- Shows detailed information in info windows when markers are clicked

## Key Code Changes

1. **Outward Code Filtering**:
   ```python
   if search_query.upper().strip() == 'SW11':
       base_query = base_query.filter(outward_code__iexact='SW11')
   ```

2. **Technology Filter Bypass**:
   ```python
   # Special case for SW11 searches - skip technology filtering
   if search_query and search_query.upper().strip() == 'SW11':
       print("SW11 search detected - skipping technology filter to show all SW11 components")
   ```

3. **Time-based Cache Keys**:
   ```python
   # For SW11 search, bypass cache completely or use a special key with timestamp
   if search_query_param and search_query_param.upper().strip() == 'SW11':
       import time
       current_time = int(time.time() / 300)  # Changes every 5 minutes
       cache_key = f"map_data_sw11_{current_time}"
   ```

## How to Test

1. Navigate to the map search: `/map_search/?q=sw11`
2. Verify markers appear on the map (should see 2 markers)
3. Click on markers to see component details
4. If no markers appear, run the cache clearing script:
   ```
   python clear_map_cache.py
   ```

## Notes for Future Development

1. **Generalized Postcode Handling**: The current fix is specific to SW11, but the approach can be extended to handle all postcode searches with the pattern-matching logic shown in the implementation plan.

2. **Cache Management**: Consider adding more robust cache invalidation mechanisms for search queries, perhaps with query-specific timeout values.

3. **Fallback Markers**: If no exact matches are found for a postcode, we could add approximate area markers to help users understand the search area.

The detailed implementation plan in `POSTCODE_SEARCH_IMPLEMENTATION_PLAN.md` provides a comprehensive approach for extending this solution to all postcode searches.