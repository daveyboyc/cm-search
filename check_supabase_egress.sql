-- Supabase Log Queries to Identify Egress Culprits

-- 1. Check API request volume by endpoint (last 24 hours)
SELECT 
    path,
    method,
    COUNT(*) as request_count,
    SUM(response_size) as total_bytes,
    ROUND(SUM(response_size) / 1024 / 1024, 2) as total_mb,
    ROUND(AVG(response_size) / 1024, 2) as avg_kb_per_request,
    ROUND(SUM(response_size) / 1024 / 1024 / 1024, 2) as total_gb
FROM 
    edge_logs
WHERE 
    timestamp >= NOW() - INTERVAL '24 hours'
    AND status_code = 200
GROUP BY 
    path, method
ORDER BY 
    total_bytes DESC
LIMIT 20;

-- 2. Check database query patterns and data transfer
SELECT 
    query,
    COUNT(*) as execution_count,
    SUM(rows_returned) as total_rows,
    ROUND(AVG(duration_ms), 2) as avg_duration_ms,
    ROUND(SUM(rows_returned * avg_row_size) / 1024 / 1024, 2) as estimated_mb
FROM 
    postgres_logs
WHERE 
    timestamp >= NOW() - INTERVAL '24 hours'
    AND query NOT LIKE '%pg_%' -- Exclude system queries
GROUP BY 
    query
ORDER BY 
    total_rows DESC
LIMIT 20;

-- 3. Check egress by table
SELECT 
    table_name,
    operation,
    COUNT(*) as operation_count,
    SUM(row_count) as total_rows,
    ROUND(SUM(data_size) / 1024 / 1024, 2) as total_mb
FROM 
    table_activity_logs
WHERE 
    timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY 
    table_name, operation
ORDER BY 
    total_mb DESC;

-- 4. Identify large response patterns
SELECT 
    path,
    COUNT(*) as request_count,
    MAX(response_size) / 1024 / 1024 as max_mb,
    MIN(response_size) / 1024 as min_kb,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_size) / 1024 / 1024 as p95_mb
FROM 
    edge_logs
WHERE 
    timestamp >= NOW() - INTERVAL '24 hours'
    AND response_size > 1024 * 1024 -- Only responses > 1MB
GROUP BY 
    path
ORDER BY 
    max_mb DESC;

-- 5. Check hourly egress pattern
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as requests,
    ROUND(SUM(response_size) / 1024 / 1024 / 1024, 2) as gb_transferred
FROM 
    edge_logs
WHERE 
    timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY 
    hour
ORDER BY 
    hour DESC;
