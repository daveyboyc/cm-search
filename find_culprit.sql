-- Find which tables/queries are causing most data transfer
WITH table_sizes AS (
    SELECT 
        tablename,
        pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size,
        pg_total_relation_size(tablename::regclass) as size_bytes
    FROM pg_tables 
    WHERE schemaname = 'public'
)
SELECT 
    t.tablename,
    t.size as table_size,
    s.n_tup_fetched as total_rows_fetched,
    CASE 
        WHEN s.n_tup_fetched > 0 
        THEN ROUND((t.size_bytes::numeric * s.n_tup_fetched) / COUNT(*) OVER() / 1024 / 1024 / 1024, 2)
        ELSE 0 
    END as estimated_gb_transferred
FROM table_sizes t
JOIN pg_stat_user_tables s ON t.tablename = s.tablename
WHERE s.schemaname = 'public'
ORDER BY s.n_tup_fetched DESC;
