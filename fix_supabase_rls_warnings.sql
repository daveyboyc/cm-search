-- Fix Supabase RLS Warnings
-- This script enables RLS on tables but sets permissive policies since this is a public application

-- 1. Enable RLS on user profile table (needs user-specific access)
ALTER TABLE public.accounts_userprofile ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own profile
CREATE POLICY "Users can view own profile" ON public.accounts_userprofile
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Policy: Users can update their own profile  
CREATE POLICY "Users can update own profile" ON public.accounts_userprofile
    FOR UPDATE USING (auth.uid()::text = user_id::text);

-- 2. Enable RLS on registration email records (admin/system only)
ALTER TABLE public.accounts_registrationemailrecord ENABLE ROW LEVEL SECURITY;

-- Policy: Only service role can access registration records
CREATE POLICY "Service role can manage registration records" ON public.accounts_registrationemailrecord
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 3. Enable RLS on checker_companylinks (public read access)
ALTER TABLE public.checker_companylinks ENABLE ROW LEVEL SECURITY;

-- Policy: Public read access for company links
CREATE POLICY "Public read access for company links" ON public.checker_companylinks
    FOR SELECT USING (true);

-- Policy: Only service role can modify company links
CREATE POLICY "Service role can modify company links" ON public.checker_companylinks
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 4. Enable RLS on checker_locationgroup (public read access)
ALTER TABLE public.checker_locationgroup ENABLE ROW LEVEL SECURITY;

-- Policy: Public read access for location groups
CREATE POLICY "Public read access for location groups" ON public.checker_locationgroup
    FOR SELECT USING (true);

-- Policy: Only service role can modify location groups
CREATE POLICY "Service role can modify location groups" ON public.checker_locationgroup
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 5. Enable RLS on Django system tables (service role only)
ALTER TABLE public.django_migrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages migrations" ON public.django_migrations
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

ALTER TABLE public.django_content_type ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages content types" ON public.django_content_type
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

ALTER TABLE public.auth_permission ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages permissions" ON public.auth_permission
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN (
    'accounts_userprofile',
    'checker_companylinks', 
    'checker_locationgroup',
    'accounts_registrationemailrecord',
    'django_migrations',
    'django_content_type',
    'auth_permission'
)
ORDER BY tablename;