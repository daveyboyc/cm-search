-- Fix RLS for the 13 tables that have it disabled
-- This script enables RLS and creates appropriate policies

-- =============================================
-- 1. AUTH TABLES (Django Auth System)
-- =============================================

-- auth_group
ALTER TABLE public.auth_group ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages groups" ON public.auth_group
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- auth_group_permissions
ALTER TABLE public.auth_group_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages group permissions" ON public.auth_group_permissions
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- auth_permission
ALTER TABLE public.auth_permission ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages permissions" ON public.auth_permission
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- auth_user (Django User model - needs special handling)
ALTER TABLE public.auth_user ENABLE ROW LEVEL SECURITY;
-- Public can see usernames (for display purposes)
CREATE POLICY "Public can view basic user info" ON public.auth_user
    FOR SELECT USING (true);
-- Service role can manage all users
CREATE POLICY "Service role manages users" ON public.auth_user
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- auth_user_groups
ALTER TABLE public.auth_user_groups ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages user groups" ON public.auth_user_groups
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- auth_user_user_permissions  
ALTER TABLE public.auth_user_user_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages user permissions" ON public.auth_user_user_permissions
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================
-- 2. DJANGO SYSTEM TABLES
-- =============================================

-- django_admin_log
ALTER TABLE public.django_admin_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages admin logs" ON public.django_admin_log
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- django_content_type
ALTER TABLE public.django_content_type ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages content types" ON public.django_content_type
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- django_migrations
ALTER TABLE public.django_migrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages migrations" ON public.django_migrations
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- django_session
ALTER TABLE public.django_session ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages sessions" ON public.django_session
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================
-- 3. CHECKER APP TABLES  
-- =============================================

-- checker_cmuregistry
ALTER TABLE public.checker_cmuregistry ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access for cmu registry" ON public.checker_cmuregistry
    FOR SELECT USING (true);
CREATE POLICY "Service role can modify cmu registry" ON public.checker_cmuregistry
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- checker_component (main data table - public read access)
ALTER TABLE public.checker_component ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access for components" ON public.checker_component
    FOR SELECT USING (true);
CREATE POLICY "Service role can modify components" ON public.checker_component
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- components (if this is a separate table)
ALTER TABLE public.components ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access for components table" ON public.components
    FOR SELECT USING (true);
CREATE POLICY "Service role can modify components table" ON public.components
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================
-- 4. VERIFICATION  
-- =============================================

-- Check that all 13 tables now have RLS enabled
SELECT 
    tablename,
    CASE 
        WHEN rowsecurity THEN '✅ RLS ENABLED' 
        ELSE '❌ RLS DISABLED' 
    END as status
FROM pg_tables 
WHERE schemaname = 'public'
    AND tablename IN (
        'auth_group',
        'auth_group_permissions', 
        'auth_permission',
        'auth_user',
        'auth_user_groups',
        'auth_user_user_permissions',
        'django_admin_log',
        'django_content_type',
        'django_migrations',
        'django_session',
        'checker_cmuregistry',
        'checker_component',
        'components'
    )
ORDER BY tablename;