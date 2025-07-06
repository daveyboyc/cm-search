# Archived Documentation

This directory contains historical documentation from major optimization and implementation efforts. These documents provide detailed context for architectural decisions and can help prevent regressions.

## 📂 Performance Optimizations

### Egress Reduction (2025)
- **EGRESS_REDUCTION_SUMMARY.md** - June 2025 LocationGroup JSON field optimization (82% reduction)
- **EGRESS_OPTIMIZATION_VERIFICATION_GUIDE.md** - Testing and verification procedures
- **debug_egress_spike.md** - Debugging guide for egress monitoring

### Database & Query Optimization
- **LOCATION_SEARCH_OPTIMIZATION.md** - LocationGroup model implementation details
- **LOCATION_SEARCH_OPTIMIZATION_STATUS.md** - Implementation status tracking
- **COMPANY_MAP_OPTIMIZATION_SUMMARY.md** - Company detail page optimization
- **COMPANY_OPTIMIZATION_SUMMARY.md** - General company view improvements
- **TECHNOLOGY_SEARCH_OPTIMIZATION_COMPLETE.md** - Technology page optimizations
- **TECHNOLOGY_PERFORMANCE_VERIFICATION.md** - Performance testing results

### Redis & Caching
- **REDIS_OPTIMIZATION.md** - Redis usage optimization strategies
- **REDIS_OPTIMIZATION_GUIDE.md** - Detailed Redis memory management
- **REDIS_AND_CACHE_USAGE.md** - Cache architecture documentation

## 🗺️ Map Feature Development

### Map Search Implementation
- **MAP_SEARCH_FIX.md** - Postcode search improvements for map view
- **SW11_MAP_SEARCH_FIX_SUMMARY.md** - Specific SW11 postcode bug fix
- **SIMPLIFIED_MAP_SOLUTION.md** - Map architecture simplification
- **VIEW_ON_MAP_IMPLEMENTATION.md** - Map integration with search results

### Map Performance
- **MAP_VIEWS_DEFAULT_ANALYSIS.md** - Default map view behavior analysis
- **COMPREHENSIVE_MAP_SEARCH_PLAN.md** - Complete map search strategy

## 🏗️ Architecture & Infrastructure

### Database Models
- **LOCATIONGROUP_EXPANSION_PLAN.md** - LocationGroup model design and implementation
- **location_grouping_solution_summary.md** - Component grouping strategy

### Search Implementation  
- **SEARCH_IMPLEMENTATION.md** - Core search functionality
- **SEARCH_AND_OPTIMIZATION.md** - Search performance improvements
- **SEARCH_OPTIMIZATION_COMPLETE.md** - Final search optimization status
- **POSTCODE_SEARCH_IMPLEMENTATION_PLAN.md** - Postcode handling strategy

### URL & Navigation
- **URL_HIERARCHY_IMPLEMENTATION_COMPLETE.md** - URL structure implementation
- **URL_STRUCTURE_ANALYSIS.md** - URL design analysis
- **DROPDOWN_IMPLEMENTATION_ANALYSIS.md** - Filter dropdown implementation

## 🧹 Development Process

### Code Organization
- **CLEANUP_TEST_FILES.md** - Test file organization and pytest setup
- **pagination_improvements.md** - Pagination fixes and optimizations
- **FIXED_OPTIMIZATION_SUMMARY.md** - Summary of completed optimizations

### Documentation & Planning
- **SIMPLIFIED_OPTIMIZATION_SUMMARY.md** - High-level optimization overview
- **PERFORMANCE_FIX_SUMMARY.md** - Performance improvement tracking
- **UNIVERSAL_COMPANY_FIX_SUMMARY.md** - Company page fixes

### Alternative Approaches (Historical)
- **README_SUPABASE.md** - Previous Supabase integration attempt
- **README_SUPABASE_DIRECT.md** - Direct Supabase approach
- **README_HYBRID_OPTIMIZATION.md** - Hybrid optimization strategies
- **README_LOCAL_OPTIMIZATION.md** - Local development optimization
- **MULTI_PLATFORM_ARCHITECTURE.md** - Multi-platform considerations

## 📊 Key Lessons Learned

### Major Optimizations (Prevent Regressions)
1. **Never fetch all result IDs for filter building** - Use sampling (max 500)
2. **Pre-compute location aggregations** - Don't group at runtime
3. **Use database-level filtering** - Avoid Python loops on large datasets
4. **Static files for location mappings** - Don't store 71GB in Redis
5. **Monitor egress carefully** - Small code changes can cause massive usage spikes

### Performance Principles
- **Database first**: PostgreSQL JSON operations are faster than Python processing
- **Sample, don't enumerate**: For UI dropdowns, 500 samples provide enough variety
- **Cache expensively computed data**: But not at the cost of memory pressure
- **Monitor during development**: Egress spikes are easier to fix before deployment

### Architecture Decisions
- **LocationGroup model**: Pre-aggregated data eliminates expensive runtime grouping
- **GIN indexes**: Essential for PostgreSQL JSON field performance
- **Sampling approach**: Maintains UI functionality while controlling data transfer
- **Static JSON files**: Better than Redis for read-heavy, infrequently updated data

---

**Note**: When implementing new features, check these archived docs first to understand what optimizations are already in place and what approaches have been tried before.