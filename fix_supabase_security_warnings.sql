-- Fix Supabase Security Warnings
-- Run this script in your Supabase SQL Editor

-- 1. Fix Function Search Path Mutable warning
-- Drop the unused trigger and function
DROP TRIGGER IF EXISTS search_vector_update ON checker_component;
DROP FUNCTION IF EXISTS public.components_search_vector_update() CASCADE;

-- 2. Fix Extension in Public warning
-- Create a dedicated schema for extensions
CREATE SCHEMA IF NOT EXISTS extensions;

-- Grant usage on extensions schema to necessary roles
GRANT USAGE ON SCHEMA extensions TO postgres;
GRANT USAGE ON SCHEMA extensions TO authenticated;
GRANT USAGE ON SCHEMA extensions TO service_role;
GRANT USAGE ON SCHEMA extensions TO anon;

-- Move pg_trgm extension to the extensions schema
DROP EXTENSION IF EXISTS pg_trgm CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA extensions;

-- Note: The search path is automatically handled by Supabase
-- Extensions in dedicated schema will be accessible when needed

-- Verify the changes
SELECT 
    'Function cleaned up' as status,
    NOT EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'components_search_vector_update'
    ) as success

UNION ALL

SELECT 
    'Extension moved' as status,
    EXISTS (
        SELECT 1 FROM pg_extension e
        JOIN pg_namespace n ON e.extnamespace = n.oid
        WHERE e.extname = 'pg_trgm' AND n.nspname = 'extensions'
    ) as success;