# Egress and Redis Optimization Plan

## Overview
Comprehensive plan to reduce Supabase egress and optimize Redis usage for the CMR project. Current Supabase usage: 225MB (checker_component table), targeting <5GB/month total egress limit.

## Current State Analysis

### Database Size Breakdown
- **checker_component**: 225MB (63,847 rows) - PRIMARY CONCERN
- **checker_cmuregistry**: 29MB 
- **checker_locationgroup**: 28MB (optimization table)
- Total database size: ~300MB

### Egress Monitoring
Use Supabase MCP tools to monitor egress:
```bash
# Check current egress usage
mcp__supabase__get_logs --service=postgres
mcp__supabase__execute_sql --query="SELECT pg_size_pretty(pg_database_size('postgres'))"
```

## Critical Egress Issues Identified

### 1. Component Table Fallback Queries (HIGHEST PRIORITY)
**Issue**: When LocationGroup returns <3 results, system falls back to expensive Component table queries
**Impact**: 15-30MB per fallback query
**Location**: `checker/services/component_search_optimized_v2.py:174-175`

### 2. Map API Bypass
**Issue**: Map data requests bypass LocationGroup optimization entirely
**Impact**: Queries all 63K components for viewport data
**Location**: `checker/views.py:2959`

### 3. Multi-word Search Pattern
**Issue**: Always hits Component table regardless of LocationGroup coverage
**Impact**: Every multi-word search = expensive query

### 4. Technology Dropdown Queries
**Issue**: Scans entire Component table for distinct technology values
**Impact**: Runs on every filter page load

## Optimization Strategy

### Phase 1: Immediate Wins (1-2 days)

#### 1.1 Reduce Fallback Threshold
- **Change**: Lower Component fallback from 3 to 1 results
- **File**: `checker/services/component_search_optimized_v2.py:174`
- **Expected Impact**: 70% reduction in fallback queries

#### 1.2 Add Query Limits
- **Implement**: Hard cap Component queries at 1000 rows
- **Location**: All Component.objects.filter() calls
- **Expected Impact**: Prevent runaway queries

#### 1.3 Cache Technology Values
- **Implement**: Pre-compute and cache technology dropdown options
- **Storage**: Redis with 24-hour TTL
- **Expected Impact**: Eliminate repeated technology scans

#### 1.4 Map Data Limits
- **Implement**: Limit map queries by viewport bounds
- **Add**: Result pagination for large map areas
- **Expected Impact**: 50% reduction in map-related egress

### Phase 2: Medium-term Optimizations (1 week)

#### 2.1 Enhanced LocationGroup Coverage
- **Goal**: Increase LocationGroup coverage from 80% to 95%
- **Method**: Include more edge cases and specific searches
- **Implementation**: Bulk update LocationGroup aggregations

#### 2.2 Multi-word Search Optimization
- **Implement**: Pre-compute common multi-word search patterns
- **Storage**: Redis cache with search results
- **Target**: Top 100 multi-word search combinations

#### 2.3 Map-Specific LocationGroups
- **Create**: Separate aggregation table for map data
- **Fields**: lat/lng bounds, technology counts, capacity totals
- **Benefits**: Map queries use lightweight aggregates

#### 2.4 Smart Caching Strategy
- **Implement**: Tiered caching system
  - L1: Redis (hot searches, 1-hour TTL)
  - L2: Database materialized views (daily refresh)
  - L3: LocationGroup fallback

### Phase 3: Long-term Architecture (2-3 weeks)

#### 3.1 Component Table Partitioning
- **Strategy**: Partition by technology or delivery_year
- **Benefits**: Smaller query scopes, improved performance
- **Risk**: Complex implementation on Supabase

#### 3.2 Search Index Optimization
- **Implement**: Full-text search indexes for common patterns
- **Technology**: PostgreSQL full-text search
- **Target**: Company names, descriptions, locations

#### 3.3 Data Archiving Strategy
- **Identify**: Old/inactive components for archival
- **Implement**: Separate archive table for historical data
- **Benefits**: Reduce main table size

## Redis Optimization Plan

### Current Redis Usage Assessment
- **Sessions**: Django session storage
- **Cache**: Search result caching
- **Rate Limiting**: API throttling data

### Redis Optimization Actions

#### 1. Cache TTL Optimization
```python
# Current approach - optimize TTLs based on data volatility
CACHE_SETTINGS = {
    'search_results': 3600,  # 1 hour
    'technology_list': 86400,  # 24 hours  
    'location_groups': 43200,  # 12 hours
    'map_data': 1800,  # 30 minutes
}
```

#### 2. Memory-Efficient Caching
- **Implement**: Compress large cached objects
- **Use**: Redis compression for search results >100KB
- **Target**: 40% memory reduction

#### 3. Cache Invalidation Strategy
- **Smart Invalidation**: Only clear relevant cache keys on data updates
- **Implement**: Cache tagging for related data groups
- **Benefits**: Reduce cache rebuild overhead

## Monitoring and Alerts

### 1. Egress Monitoring
```bash
# Daily egress check (add to cron)
mcp__supabase__execute_sql --query="
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"
```

### 2. Performance Monitoring
- **Implement**: Middleware to track query response sizes
- **Alert**: Queries >50MB egress
- **Log**: Component table fallback events

### 3. Redis Memory Monitoring
- **Track**: Redis memory usage trends
- **Alert**: >80% memory utilization
- **Optimize**: Automatic cache eviction policies

## Implementation Timeline

### Week 1: Critical Fixes
- [ ] Reduce fallback threshold to 1
- [ ] Add 1000-row query limits
- [ ] Cache technology values
- [ ] Implement map data limits

### Week 2: Coverage Improvements  
- [ ] Enhance LocationGroup coverage to 95%
- [ ] Implement multi-word search caching
- [ ] Create map-specific aggregations

### Week 3: Architecture Optimization
- [ ] Implement tiered caching
- [ ] Full-text search indexes
- [ ] Component table analysis for partitioning

### Week 4: Monitoring & Documentation
- [ ] Deploy egress monitoring
- [ ] Performance alerting system
- [ ] Documentation updates

## Success Metrics

### Egress Reduction Targets
- **Current**: ~1-2GB/month estimated
- **Phase 1 Target**: <800MB/month
- **Phase 2 Target**: <500MB/month  
- **Phase 3 Target**: <300MB/month

### Performance Targets
- **Search Response Time**: <2 seconds (95th percentile)
- **Map Load Time**: <3 seconds
- **Component Fallback Rate**: <5% of total searches

### Redis Efficiency
- **Memory Usage**: <512MB peak
- **Cache Hit Rate**: >85%
- **Cache Invalidation**: <10% daily churn

## Emergency Procedures

### Egress Limit Breach
1. **Immediate**: Disable expensive Component table queries
2. **Fallback**: Serve cached results only
3. **Investigation**: Use Supabase MCP tools to identify culprit queries
4. **Recovery**: Implement emergency query limits

### Redis Memory Issues
1. **Immediate**: Flush non-critical caches
2. **Temporary**: Reduce cache TTLs by 50%
3. **Investigation**: Identify memory-heavy cache keys
4. **Recovery**: Implement selective cache eviction

## Tools and Commands

### Supabase MCP Monitoring
```bash
# Check database size
mcp__supabase__execute_sql --query="SELECT pg_size_pretty(pg_database_size('postgres'))"

# Monitor table sizes
mcp__supabase__execute_sql --query="SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10"

# Check recent logs
mcp__supabase__get_logs --service=postgres
mcp__supabase__get_logs --service=api

# Performance advisors
mcp__supabase__get_advisors --type=performance
mcp__supabase__get_advisors --type=security
```

### Redis Monitoring
```bash
# Redis memory usage
redis-cli info memory

# Key count by pattern
redis-cli --scan --pattern "search:*" | wc -l

# Large keys identification
redis-cli --bigkeys
```

## Notes
- Monitor egress daily using Supabase MCP tools
- Test all optimizations locally before deploying
- Keep fallback mechanisms for optimization failures
- Document all changes for future reference