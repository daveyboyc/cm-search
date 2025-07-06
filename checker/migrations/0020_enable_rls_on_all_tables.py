# Generated manually to fix RLS warnings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0019_enable_row_level_security'),
    ]

    operations = [
        # Enable RLS on checker_component
        migrations.RunSQL(
            sql="ALTER TABLE checker_component ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE checker_component DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE POLICY "Public read access for components" ON checker_component
                    FOR SELECT USING (true);
            """,
            reverse_sql='DROP POLICY IF EXISTS "Public read access for components" ON checker_component;',
        ),
        migrations.RunSQL(
            sql="""
                CREATE POLICY "Service role can modify components" ON checker_component
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
            """,
            reverse_sql='DROP POLICY IF EXISTS "Service role can modify components" ON checker_component;',
        ),
        
        # Enable RLS on checker_cmuregistry
        migrations.RunSQL(
            sql="ALTER TABLE checker_cmuregistry ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE checker_cmuregistry DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE POLICY "Public read access for cmu registry" ON checker_cmuregistry
                    FOR SELECT USING (true);
            """,
            reverse_sql='DROP POLICY IF EXISTS "Public read access for cmu registry" ON checker_cmuregistry;',
        ),
        migrations.RunSQL(
            sql="""
                CREATE POLICY "Service role can modify cmu registry" ON checker_cmuregistry
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
            """,
            reverse_sql='DROP POLICY IF EXISTS "Service role can modify cmu registry" ON checker_cmuregistry;',
        ),
        
        # Enable RLS on Django/Auth system tables (all service role only)
        migrations.RunSQL(
            sql="""
                -- Auth tables
                ALTER TABLE auth_group ENABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_group_permissions ENABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_permission ENABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_user ENABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_user_groups ENABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_user_user_permissions ENABLE ROW LEVEL SECURITY;
                
                -- Django tables
                ALTER TABLE django_admin_log ENABLE ROW LEVEL SECURITY;
                ALTER TABLE django_content_type ENABLE ROW LEVEL SECURITY;
                ALTER TABLE django_migrations ENABLE ROW LEVEL SECURITY;
                ALTER TABLE django_session ENABLE ROW LEVEL SECURITY;
            """,
            reverse_sql="""
                -- Auth tables
                ALTER TABLE auth_group DISABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_group_permissions DISABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_permission DISABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_user DISABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_user_groups DISABLE ROW LEVEL SECURITY;
                ALTER TABLE auth_user_user_permissions DISABLE ROW LEVEL SECURITY;
                
                -- Django tables
                ALTER TABLE django_admin_log DISABLE ROW LEVEL SECURITY;
                ALTER TABLE django_content_type DISABLE ROW LEVEL SECURITY;
                ALTER TABLE django_migrations DISABLE ROW LEVEL SECURITY;
                ALTER TABLE django_session DISABLE ROW LEVEL SECURITY;
            """,
        ),
        
        # Create policies for auth/django tables
        migrations.RunSQL(
            sql="""
                -- Auth tables policies
                CREATE POLICY "Service role manages groups" ON auth_group
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages group permissions" ON auth_group_permissions
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages permissions" ON auth_permission
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Public can view basic user info" ON auth_user
                    FOR SELECT USING (true);
                CREATE POLICY "Service role manages users" ON auth_user
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages user groups" ON auth_user_groups
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages user permissions" ON auth_user_user_permissions
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                
                -- Django tables policies
                CREATE POLICY "Service role manages admin logs" ON django_admin_log
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages content types" ON django_content_type
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages migrations" ON django_migrations
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                CREATE POLICY "Service role manages sessions" ON django_session
                    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
            """,
            reverse_sql="""
                -- Drop all policies
                DROP POLICY IF EXISTS "Service role manages groups" ON auth_group;
                DROP POLICY IF EXISTS "Service role manages group permissions" ON auth_group_permissions;
                DROP POLICY IF EXISTS "Service role manages permissions" ON auth_permission;
                DROP POLICY IF EXISTS "Public can view basic user info" ON auth_user;
                DROP POLICY IF EXISTS "Service role manages users" ON auth_user;
                DROP POLICY IF EXISTS "Service role manages user groups" ON auth_user_groups;
                DROP POLICY IF EXISTS "Service role manages user permissions" ON auth_user_user_permissions;
                DROP POLICY IF EXISTS "Service role manages admin logs" ON django_admin_log;
                DROP POLICY IF EXISTS "Service role manages content types" ON django_content_type;
                DROP POLICY IF EXISTS "Service role manages migrations" ON django_migrations;
                DROP POLICY IF EXISTS "Service role manages sessions" ON django_session;
            """,
        ),
        
        # Handle the 'components' table if it exists (might be a view or old table)
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'components' AND schemaname = 'public') THEN
                        ALTER TABLE components ENABLE ROW LEVEL SECURITY;
                        CREATE POLICY "Public read access for components table" ON components
                            FOR SELECT USING (true);
                        CREATE POLICY "Service role can modify components table" ON components
                            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'components' AND schemaname = 'public') THEN
                        DROP POLICY IF EXISTS "Public read access for components table" ON components;
                        DROP POLICY IF EXISTS "Service role can modify components table" ON components;
                        ALTER TABLE components DISABLE ROW LEVEL SECURITY;
                    END IF;
                END $$;
            """,
        ),
    ]