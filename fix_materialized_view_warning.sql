-- Optional: Fix materialized view warning by restricting access
-- This is typically NOT needed for public aggregated data like technology summaries
-- Only apply this if you don't want anonymous users to access the summary data

-- Option 1: Remove public access to materialized view
-- REVOKE SELECT ON public.technology_summary FROM anon;
-- REVOKE SELECT ON public.technology_summary FROM authenticated;

-- Option 2: Keep public access (recommended for aggregated data)
-- No action needed - this warning is acceptable for public summary data

-- To verify current permissions:
SELECT 
    schemaname,
    matviewname,
    matviewowner,
    hasselect,
    hasinsert,
    hasupdate,
    hasdelete
FROM pg_matviews 
LEFT JOIN information_schema.table_privileges ON table_name = matviewname
WHERE matviewname = 'technology_summary';