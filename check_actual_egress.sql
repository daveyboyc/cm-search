-- Actual queries you can run in Supabase SQL Editor

-- 1. Check Component table access patterns (main culprit likely)
SELECT 
    COUNT(*) as query_count,
    pg_size_pretty(SUM(pg_relation_size('checker_component'))) as table_size
FROM pg_stat_user_tables 
WHERE schemaname = 'public' 
AND tablename = 'checker_component';

-- 2. Check LocationGroup table access
SELECT 
    COUNT(*) as query_count,
    pg_size_pretty(SUM(pg_relation_size('checker_locationgroup'))) as table_size
FROM pg_stat_user_tables 
WHERE schemaname = 'public' 
AND tablename = 'checker_locationgroup';

-- 3. Estimate data transfer by counting large queries
-- This shows which tables are being queried most
SELECT 
    schemaname,
    tablename,
    n_tup_fetched as rows_fetched,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
FROM 
    pg_stat_user_tables
WHERE 
    schemaname = 'public'
ORDER BY 
    n_tup_fetched DESC
LIMIT 10;

-- 4. Check index usage (poor indexes = more data scanned)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as rows_read_via_index,
    idx_tup_fetch as rows_fetched_via_index
FROM 
    pg_stat_user_indexes
WHERE 
    schemaname = 'public'
ORDER BY 
    idx_scan DESC
LIMIT 20;
