# Location Grouping Solution Summary

## Key Findings

### 1. Capacity Data Availability
- **7.7%** have `derated_capacity_mw` in the main field
- **~21%** have capacity in `additional_data['De-Rated Capacity']`
- **~21%** have capacity in `additional_data['Connection / DSR Capacity']`
- Many components have NO capacity data at all

### 2. Capacity Calculation Strategy

```python
# Priority order for getting capacity:
1. component.derated_capacity_mw (most reliable)
2. additional_data['De-Rated Capacity']
3. additional_data['Connection / DSR Capacity'] 
4. CMU Registry data (if available)
```

For location totals:
- Group by unique description (Engine 1, Engine 2, etc.)
- Use the mode (most common value) per asset
- Sum the unique assets (not all components)

### 3. Raw Data Handling

Since each component has unique raw data (CMU data + component data), we propose:

#### On-Demand Loading
```javascript
// Location page loads with summary only
// User clicks "View Raw Data" for a specific component
fetch(`/api/component/${componentId}/raw-data/`)
  .then(response => response.json())
  .then(data => {
    // Display CMU Registry data
    // Display Component additional_data
  });
```

#### API Endpoints
- `/api/component/{id}/raw-data/` - Individual component raw data
- `/api/location/{location_id}/all-raw-data/` - Bulk download
- `/api/cmu/{cmu_id}/registry-data/` - CMU registry data

### 4. Database Structure

```python
class LocationGroup(models.Model):
    location = models.CharField(max_length=255, unique=True)
    
    # Aggregated data
    total_capacity_mw = models.FloatField()  # Calculated sum
    capacity_confidence = models.CharField()  # high/medium/low
    
    # JSON fields for flexibility
    assets = models.JSONField()  # {description: {capacity, count, cmu_ids}}
    capacity_breakdown = models.JSONField()  # Details of calculation
```

### 5. Search/Pagination Benefits

Current "battery" search:
- 3,883 components → Complex pagination
- Fetching subsets causes issues

With location grouping:
- 2,228 unique locations → Simple pagination
- Each result = 1 location (not 1 component)
- No more partial fetching issues

### 6. Migration Strategy

1. **Phase 1**: Build LocationGroup table alongside existing structure
2. **Phase 2**: Update search to use LocationGroup for results
3. **Phase 3**: Keep component detail pages but add location pages
4. **Phase 4**: Gradually migrate users to location-based views

### 7. Example: Imperial College

Before:
- 18 separate component pages
- Duplicate data (Engine 1 appears 9 times)
- Confusing capacity info

After:
- 1 location page
- 2 assets clearly shown (Engine 1, Engine 2)
- Capacity: 8.1 MW (2 × 4.05 MW)
- Raw data available on demand

## Implementation Steps

1. Create LocationGroup model ✅
2. Build management command to populate it
3. Create API endpoints for raw data
4. Update search to use LocationGroup
5. Create location detail pages
6. Add "View Raw Data" functionality
7. Test and optimize performance