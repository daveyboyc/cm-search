# Current Development Priorities

## 🚨 Critical Issues

### Registration & Authentication
- [ ] **Fix activation link token mismatch**
  - Issue: Users re-registering with same email get invalid activation tokens
  - Cause: Password update invalidates old token, but user tries old email link
  - Solution: Provide "resend activation email" feature or better error messaging

### CloudFlare Caching Issues  
- [ ] **Clear CloudFlare cache for component URLs**
  - Issue: Component detail pages (e.g. `/component/60598/`) showing 405 errors
  - Cause: CloudFlare caching old error responses
  - Solution: Clear cache for `/component/*` URL pattern in CloudFlare dashboard

## 🎯 Performance & Cost Optimization

### Search Performance Optimization (URGENT)
- [ ] **Fix 3-5 second search delays**
  - Issue: Search for "boots" takes 3.1s despite showing "0 database queries"
  - Root cause: Missing trigram indexes for ILIKE searches on location field
  - Solutions:
    1. Run migration `0024_add_trgm_indexes.py` to add GIN trigram indexes
    2. Run `python manage.py warm_search_cache` to pre-cache common searches
    3. Monitor with `mcp__supabase__execute_sql` to verify index usage
  - Expected improvement: 3-5s → <500ms

### Comprehensive Egress & Redis Optimization
- [x] **Deployment egress optimization** ✅ (2025-01-21)
  - ✅ Removed cache building from deployment script (saves 1-10MB per deployment)
  - ✅ Added `--light` and `--check-changes` flags to management commands
  - ✅ Created post-crawl cache rebuild workflow
  - ✅ Tested: `--light` mode skips rebuild when cache exists (zero egress)
- [ ] **Follow remaining EGRESS_OPTIMIZATION.md plan**
  - See [EGRESS_OPTIMIZATION.md](EGRESS_OPTIMIZATION.md) for complete optimization strategy
  - Use Supabase MCP tools for monitoring: `mcp__supabase__get_logs`, `mcp__supabase__execute_sql`
  - Next: Analyze Component table fallback patterns in production logs

### Egress Reduction for Free Tier
- [ ] **Switch default navigation to list view** 
  - Change "Locations" nav menu to point to `/search/` instead of `/search-map/`
  - Map view loads coordinate data increasing egress
  - Target: Reduce daily usage from 2.5GB to <500MB

- [ ] **Reduce default page size**
  - Change from 25 to 10 results per page in views
  - Apply to both search and map views

- [ ] **Implement aggressive bot blocking**
  - Add User-Agent filtering for crawlers/bots
  - Rate limit requests to 10/minute per IP
  - Return 403 for common bot signatures

## 📱 User Experience

### New Mobile-Optimized Map View (HIGH PRIORITY)
- [ ] **Create new map view with better mobile support**
  - Current `/map/` has non-working satellite/street view buttons on mobile
  - New map should use universal search navbar (like current search bar redirects to map_results)
  - Desktop: Filters as dropdowns on the left sidebar
  - Mobile: Filters move to top and become collapsible
  - Standard Google Map layout with responsive filter positioning
  - Route: Consider `/map-v2/` or `/new-map/` for development

### Mobile Optimization
- [ ] **Test component detail page mobile layout**
  - Verify map integration works on mobile devices
  - Check badge responsive design at various screen sizes

### Search Improvements  
- [ ] **Add search suggestions/autocomplete**
  - Use LocationGroup data for location suggestions
  - Cache common search terms for performance

## 🛠️ Technical Debt

### Code Cleanup
- [ ] **Remove deprecated logo files**
  - Delete `capacity_checker/staticfiles/images/favicon_backup.png`
  - Delete `capacity_checker/staticfiles/images/favicon_fill_backup.png`
  - Keep only: `static/images/favicon.png` (green lightning pin)

- [ ] **Remove unused optimized search/list view templates**
  - May delete unnecessary optimized search and list view templates now they are not being used
  - Templates affected: search_components_optimized views, list view functionality
  - Consider removal after confirming no dependencies remain

### Documentation Maintenance
- [x] **Archive historical documentation** ✅
  - Moved 40+ MD files to `docs/archive/`
  - Cleaned up README.md with current architecture
  - Preserved optimization history for future reference

### Testing Infrastructure
- [ ] **Expand test coverage**
  - Add tests for LocationGroup model and views
  - Test access control middleware
  - Integration tests for search functionality

## 🔮 Future Enhancements

### Advanced Features
- [ ] **Export functionality**
  - CSV/Excel export for search results
  - Requires premium access
  - Limit to 1000 results max

- [ ] **Saved searches**
  - Allow users to bookmark common searches
  - Email alerts for new components matching saved criteria

### Analytics
- [ ] **Usage tracking dashboard**
  - Track popular search terms
  - Monitor egress patterns by feature
  - User engagement metrics

## ✅ Recently Completed (2025)

### Major Performance Optimizations
- [x] **Fixed 8MB egress regression** (June 16)
  - Regular search was fetching 16,034 rows instead of 500 samples
  - Reduced per-search egress from 8MB → 26KB (99.7% improvement)

- [x] **Updated navigation to use map view** (June 16)
  - "Locations" menu now points to optimized map search
  - Consistent user experience across navigation

- [x] **Fixed search display issue** (June 16) 
  - Search results showing "All locations" instead of search terms
  - Added missing 'query' context variable to template

- [x] **Fixed background image loading** (June 16)
  - Ran collectstatic on Heroku to properly serve static files
  - Background images now load consistently

### Access Control System (June 15)
- [x] **Implemented 2-tier access control**
  - Free tier: Basic search and limited map access
  - Trial tier: 1-minute full access for testing
  - Payment integration with Stripe for premium access

### Core Architecture (2025)
- [x] **LocationGroup model implementation**
  - Pre-computed location aggregations eliminate runtime grouping
  - 82% reduction in database egress
  - GIN indexes for fast JSON field searches

- [x] **Static file optimization**
  - Moved 71.5GB Redis location mappings to 3MB JSON files
  - Location lookups: 5.6s → <10ms improvement
  - Eliminated Redis memory pressure

---

## 📋 Development Guidelines

### Before Making Changes
1. Check `docs/archive/` for relevant historical context
2. Monitor egress impact via logs during testing
3. Test on both desktop and mobile devices
4. Verify CloudFlare cache behavior for public URLs

### Performance Monitoring
- Use browser dev tools Network tab to measure egress
- Check Heroku logs for database query patterns  
- Monitor response times for search operations
- Track Redis memory usage if caching enabled

### Deployment Checklist
- [ ] Test critical user flows (search, registration, login)
- [ ] Verify static files serve correctly
- [ ] Clear CloudFlare cache if URL patterns changed
- [ ] Monitor logs for errors in first 24 hours