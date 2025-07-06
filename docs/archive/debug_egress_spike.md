# 🔍 EGRESS SPIKE DEBUGGING GUIDE

## ✅ OPTIMIZATIONS ALREADY IMPLEMENTED

I've added the following optimizations to prevent egress spikes:

### Company-Map Endpoints (`/company-map/`)
- ✅ `@gzip_page` - 70-80% compression
- ✅ `@cache_page(60 * 10)` - 10-minute caching
- ✅ `@monitor_api` - Usage tracking

### Technology-Map Endpoints (`/technology-map/`)
- ✅ `@gzip_page` - 70-80% compression  
- ✅ `@cache_page(60 * 10)` - 10-minute caching
- ✅ `@monitor_api` - Usage tracking

### API Endpoints
- ✅ `/api/search-geojson/` - Field reduction (60%), gzip, 15min cache, 100 limit
- ✅ `/api/map-data/` - Gzip compression
- ✅ `/api/component-map-detail/` - Gzip compression
- ✅ HTMX company endpoints - Gzip compression

## 🎯 BEST DEBUGGING METHOD: BROWSER DEV TOOLS

**This is the most reliable way to catch the egress spike:**

### Step 1: Open Browser Dev Tools
1. Open Chrome/Firefox
2. Press F12 or right-click > Inspect
3. Go to **Network** tab
4. Check "Disable cache" (important!)

### Step 2: Clear and Monitor
1. Click "Clear" button in Network tab
2. Navigate to the page with company links
3. Click the company link that causes the spike
4. Watch the Network tab for large responses

### Step 3: Identify Large Requests
Look for:
- **Size column** showing >100KB responses
- **Red entries** (errors that might retry)
- **API calls** to `/api/search-geojson/`, `/api/map-data/`, etc.
- **Multiple requests** to the same endpoint

### Step 4: Check Specific Details
Click on large requests to see:
- **Request URL** (exact endpoint)
- **Response size** (before/after compression)
- **Response headers** (check if gzip worked)
- **Query parameters** (check limits, filters)

## 📊 WHAT TO LOOK FOR

### Potential Culprits:
1. **Unfiltered API calls**: `/api/search-geojson/` without limit parameter
2. **Map data requests**: Large geographic datasets
3. **Sorting requests**: Database-heavy operations
4. **Cache misses**: First-time loads of heavy data
5. **Multiple parallel requests**: Several API calls at once

### Size Expectations (After Optimization):
- Company-map pages: ~97KB (compressed)
- API responses: <50KB (compressed)
- Large responses: >200KB = PROBLEM

## ⚡ QUICK TEST

**Run this simple test:**

```bash
# In one terminal, start monitoring
python simple_monitor.py

# In browser, click company link
# Monitor will show exact API calls and sizes
```

## 🚨 IF MONITORING STILL HANGS

Use **pure browser debugging**:

1. Network tab method (above) - most reliable
2. Check browser's **Memory** tab for memory spikes
3. Look at **Console** tab for JavaScript errors
4. Check **Performance** tab while clicking links

## 📋 DEBUGGING CHECKLIST

- [ ] Browser dev tools open on Network tab
- [ ] Cache disabled in dev tools
- [ ] Clicked exact company link that causes spike
- [ ] Identified request(s) >100KB
- [ ] Checked if gzip compression is working
- [ ] Noted exact endpoint URLs causing issues
- [ ] Checked query parameters on large requests

## 🎯 EXPECTED OUTCOME

With our optimizations, you should see:
- Company-map pages: <100KB
- API calls: <50KB each
- Total per click: <200KB
- **No single request >200KB**

If you see requests >200KB, that's our culprit!

## 📞 NEXT STEPS

1. Use browser dev tools to identify large requests
2. Share the exact endpoint URL and size
3. We can then optimize that specific endpoint
4. Test again to confirm the spike is eliminated

The optimizations are in place - now we need to identify which specific request is bypassing them!