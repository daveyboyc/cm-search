-- Fix Supabase RLS warnings for trades tables
-- This script enables RLS on trades tables and creates appropriate policies

-- 1. Enable RLS on trades_tradingadvert table
ALTER TABLE public.trades_tradingadvert ENABLE ROW LEVEL SECURITY;

-- Policy: Public can view active, non-expired adverts
CREATE POLICY "Public can view active adverts" ON public.trades_tradingadvert
    FOR SELECT USING (is_active = true AND expires_at > NOW());

-- Policy: Users can manage their own adverts
CREATE POLICY "Users can manage own adverts" ON public.trades_tradingadvert
    FOR ALL USING (auth.uid()::text = user_id::text);

-- Policy: Service role can manage all adverts (for admin/system operations)
CREATE POLICY "Service role can manage all adverts" ON public.trades_tradingadvert
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 2. Enable RLS on trades_tradingmessage table
ALTER TABLE public.trades_tradingmessage ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view messages for their own adverts
CREATE POLICY "Users can view messages for own adverts" ON public.trades_tradingmessage
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.trades_tradingadvert 
            WHERE id = advert_id AND user_id::text = auth.uid()::text
        )
    );

-- Policy: Users can send messages (but need INSERT permission)
CREATE POLICY "Users can send messages" ON public.trades_tradingmessage
    FOR INSERT WITH CHECK (true);

-- Policy: Service role can manage all messages
CREATE POLICY "Service role can manage all messages" ON public.trades_tradingmessage
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 3. Create RLS policies for accounts tables that are missing them

-- Policies for accounts_userprofile (if not already created)
DROP POLICY IF EXISTS "Users can view own profile" ON public.accounts_userprofile;
CREATE POLICY "Users can view own profile" ON public.accounts_userprofile
    FOR SELECT USING (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "Users can update own profile" ON public.accounts_userprofile;
CREATE POLICY "Users can update own profile" ON public.accounts_userprofile
    FOR UPDATE USING (auth.uid()::text = user_id::text);

-- Policy: Service role can manage all profiles
CREATE POLICY "Service role can manage all profiles" ON public.accounts_userprofile
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Policies for accounts_registrationemailrecord (if not already created)
DROP POLICY IF EXISTS "Service role can manage registration records" ON public.accounts_registrationemailrecord;
CREATE POLICY "Service role can manage registration records" ON public.accounts_registrationemailrecord
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Verify RLS is enabled on the problem tables
SELECT 
    schemaname, 
    tablename, 
    rowsecurity 
FROM pg_tables 
WHERE tablename IN (
    'trades_tradingadvert',
    'trades_tradingmessage',
    'accounts_userprofile',
    'accounts_registrationemailrecord'
)
ORDER BY tablename;