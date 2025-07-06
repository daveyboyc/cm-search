# Performance Optimization Report - Capacity Market Registry

## Executive Summary

This report identifies significant performance optimization opportunities in the CMR codebase, with a focus on reducing Supabase egress (currently limited to 5GB/month on free tier) and improving overall site performance.

## 1. Database Query Optimization

### High-Impact Opportunities

#### 1.1 N+1 Query Problems
- **Issue**: Multiple views don't use `select_related()` or `prefetch_related()`
- **Impact**: Each location group item triggers additional queries for related data
- **Solution**: Add proper query optimization to views

**Example Fix for views_search_map_simple.py**:
```python
# Current (inefficient)
location_groups = LocationGroup.objects.filter(...)

# Optimized
location_groups = LocationGroup.objects.filter(...).select_related(
    'representative_component'
).prefetch_related(
    'component_set'
)
```

#### 1.2 Expensive JSON Field Queries
- **Issue**: Filtering on JSON fields (companies, technologies) is expensive
- **Impact**: Full table scans on 16,000+ LocationGroup records
- **Solution**: Create materialized views or denormalized tables for common filters

**Recommendation**: Create dedicated tables for:
- CompanyLocationIndex (company_name, location_group_id)
- TechnologyLocationIndex (technology_name, location_group_id)

#### 1.3 Missing Database Indexes
- **Issue**: Some frequently queried fields lack indexes
- **Fields needing indexes**:
  - Component.status (used in active/inactive filtering)
  - LocationGroup.capacity_confidence
  - LocationGroup.is_aggregated_cmu

## 2. Caching Opportunities

### High-Impact Caching Targets

#### 2.1 Static Page Caching (Already Implemented)
- ✅ "All Locations" pages are cached (83% performance improvement achieved)
- **Further opportunity**: Extend to technology and company list pages

#### 2.2 Uncached Expensive Views
**Priority targets for caching**:
1. `/api/search-filters/` - Called on every page load, rarely changes
2. `/companies/` and `/technologies/` list views - Change infrequently
3. Map data API endpoints - Heavy GeoJSON generation

**Implementation**:
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 60)  # 1 hour cache
def search_filters_api(request):
    # Existing implementation
```

#### 2.3 Query Result Caching
- **Issue**: Same searches performed repeatedly
- **Solution**: Implement query-level caching for common searches

```python
cache_key = f"location_search:{query}:{filters}"
results = cache.get(cache_key)
if not results:
    results = expensive_query()
    cache.set(cache_key, results, timeout=300)
```

## 3. Egress Reduction Strategies

### Critical Egress Optimizations

#### 3.1 Overfetching in API Endpoints
**Problem Areas**:
- `/api/search-geojson/` returns full component data for map markers
- Company and technology views fetch all related components

**Solutions**:
1. Use `.only()` to limit fields:
```python
components = Component.objects.only(
    'id', 'latitude', 'longitude', 'location', 'technology'
)
```

2. Implement field filtering in APIs:
```python
fields = request.GET.get('fields', '').split(',')
if fields:
    queryset = queryset.only(*fields)
```

#### 3.2 JSON Field Optimization
- **Issue**: Large JSON fields (additional_data, companies, technologies) transferred unnecessarily
- **Solution**: Use `.defer()` to exclude JSON fields when not needed:

```python
location_groups = LocationGroup.objects.defer(
    'companies', 'technologies', 'descriptions', 'cmu_ids'
)
```

#### 3.3 Pagination Improvements
- **Current**: Fixed 25 items per page
- **Recommendation**: 
  - Allow user-configurable page sizes (10, 25, 50, 100)
  - Implement cursor-based pagination for large datasets
  - Add "load more" instead of full page refreshes

## 4. Static Asset Optimization

### Issues Found

#### 4.1 Large Unoptimized Images
- `industrial_background.jpeg`: 1.5MB (WebP version exists but may not be used)
- `industrial_background_dark.jpeg`: 1.2MB

**Solutions**:
1. Serve WebP with JPEG fallback:
```html
<picture>
  <source srcset="/static/images/backgrounds/industrial_background.webp" type="image/webp">
  <img src="/static/images/backgrounds/industrial_background.jpeg" alt="">
</picture>
```

2. Implement responsive images:
```html
<img srcset="image-320w.jpg 320w,
             image-640w.jpg 640w,
             image-1280w.jpg 1280w"
     sizes="(max-width: 640px) 100vw, 50vw"
     src="image-640w.jpg">
```

#### 4.2 Missing CDN Integration
- **Current**: All assets served from Heroku
- **Recommendation**: Use Cloudflare or AWS CloudFront for static assets

#### 4.3 JavaScript Loading
- Bootstrap and other libraries loaded synchronously
- No code splitting or lazy loading

**Solutions**:
- Add `async` or `defer` to script tags
- Implement dynamic imports for large libraries
- Use a bundler (Webpack/Vite) for optimization

## 5. Template Optimization

### Issues Found

#### 5.1 Expensive Template Operations
- Multiple database queries in templates (avoid `{{ location.component_set.count }}`)
- Complex filtering in templates instead of views

#### 5.2 Missing Fragment Caching
```django
{% load cache %}
{% cache 300 company_card company.id %}
    <!-- Expensive company card rendering -->
{% endcache %}
```

## 6. API Optimization

### High-Priority Optimizations

#### 6.1 Batch API Improvements
- `/api/batch-geojson/` could use HTTP/2 multiplexing
- Implement GraphQL for flexible field selection

#### 6.2 Streaming Responses
- Large GeoJSON responses should use StreamingHttpResponse
- Already implemented in `optimized_geojson_stream` - extend to other endpoints

#### 6.3 API Response Compression
- Ensure gzip is enabled for all API endpoints
- Consider Brotli compression for better ratios

## Implementation Priority

### Phase 1 (Immediate - Highest Impact)
1. **Add .only() and .defer() to all major queries** - 50-70% egress reduction
2. **Cache search_filters_api endpoint** - Reduce 1000s of daily requests
3. **Optimize image delivery** - Use WebP format, save ~2MB per page load
4. **Add database indexes** - 10-50x query speed improvement

### Phase 2 (This Week)
1. **Implement query result caching** - Reduce repeated expensive searches
2. **Create denormalized index tables** - Eliminate expensive JSON queries
3. **Add fragment caching to templates** - Reduce template rendering time
4. **Implement lazy loading for images** - Improve initial page load

### Phase 3 (This Month)
1. **Set up CDN for static assets** - Reduce server load
2. **Implement cursor-based pagination** - Better performance for large datasets
3. **Add field filtering to all APIs** - Allow clients to request only needed data
4. **Optimize JavaScript loading** - Code splitting and async loading

## Estimated Impact

Implementing these optimizations could result in:
- **80-90% reduction in Supabase egress** (from query optimization alone)
- **50-70% improvement in page load times**
- **90% reduction in server load** for common requests
- **Significant cost savings** by staying within free tier limits

## Monitoring Recommendations

1. Set up monitoring for:
   - Database query count per request
   - Egress usage by endpoint
   - Cache hit rates
   - Page load times

2. Use Django Debug Toolbar in development to catch issues early

3. Implement egress budget alerts in Supabase

## Code Examples

### Optimized View Pattern
```python
from django.views.decorators.cache import cache_page
from django.core.cache import cache

@cache_page(60 * 15)  # 15 minute page cache
def technology_list_optimized(request):
    # Check for cached data first
    cache_key = f'tech_list_{request.GET.urlencode()}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # Optimize query with only needed fields
    technologies = LocationGroup.objects.values(
        'technologies'
    ).annotate(
        total_capacity=Sum('normalized_capacity_mw'),
        location_count=Count('id')
    ).only(
        'id', 'technologies', 'normalized_capacity_mw'
    )
    
    # Process and cache results
    result = process_technologies(technologies)
    cache.set(cache_key, result, timeout=900)  # 15 minutes
    
    return result
```

### Optimized API Pattern
```python
from django.http import StreamingHttpResponse
import json

def optimized_api_endpoint(request):
    # Allow field filtering
    fields = request.GET.get('fields', '').split(',')
    
    # Base query with minimal fields
    queryset = Model.objects.only('id', 'name')
    
    # Add requested fields
    if fields:
        queryset = queryset.only(*fields)
    
    # Stream large responses
    def generate():
        yield '{"results": ['
        first = True
        for item in queryset.iterator(chunk_size=100):
            if not first:
                yield ','
            yield json.dumps(model_to_dict(item))
            first = False
        yield ']}'
    
    return StreamingHttpResponse(
        generate(),
        content_type='application/json'
    )
```

## Conclusion

The codebase has significant optimization opportunities. Focusing on database query optimization and egress reduction will provide the most immediate impact. The recommended changes can keep the site within Supabase's free tier limits while significantly improving user experience.