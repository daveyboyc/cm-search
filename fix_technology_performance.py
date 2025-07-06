#!/usr/bin/env python3
"""
Fix technology page performance issues by adding proper indexes and optimizing queries.
Run this script to apply the performance improvements.
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def create_performance_indexes():
    """Create indexes to speed up technology filtering."""
    print("🚀 Creating performance indexes for technology filtering...")
    
    with connection.cursor() as cursor:
        # 1. Functional index for UPPER() technology searches on Component
        print("\n1️⃣ Creating functional index for Component.technology...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_component_technology_upper 
                ON checker_component (UPPER(technology))
            """)
            print("✅ Created idx_component_technology_upper")
        except Exception as e:
            print(f"⚠️  Index might already exist or error: {e}")
        
        # 2. Index for technology + delivery_year (common combination)
        print("\n2️⃣ Creating composite index for technology + delivery_year...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_component_tech_year 
                ON checker_component (UPPER(technology), delivery_year DESC)
            """)
            print("✅ Created idx_component_tech_year")
        except Exception as e:
            print(f"⚠️  Index might already exist or error: {e}")
        
        # 3. Index for location + technology (for the subquery)
        print("\n3️⃣ Creating index for location + technology...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_component_loc_tech 
                ON checker_component (location, UPPER(technology))
            """)
            print("✅ Created idx_component_loc_tech")
        except Exception as e:
            print(f"⚠️  Index might already exist or error: {e}")
        
        # 4. Ensure LocationGroup has proper GIN index on technologies
        print("\n4️⃣ Ensuring GIN index on LocationGroup.technologies...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_locationgroup_tech_gin 
                ON checker_locationgroup USING gin (technologies)
            """)
            print("✅ Created idx_locationgroup_tech_gin")
        except Exception as e:
            print(f"⚠️  Index might already exist or error: {e}")
        
        # 5. Add index for LocationGroup location lookups
        print("\n5️⃣ Creating index for LocationGroup.location...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_locationgroup_location 
                ON checker_locationgroup (location)
            """)
            print("✅ Created idx_locationgroup_location")
        except Exception as e:
            print(f"⚠️  Index might already exist or error: {e}")

def analyze_current_queries():
    """Analyze current query performance."""
    print("\n📊 Analyzing current query patterns...")
    
    with connection.cursor() as cursor:
        # Check for existing indexes
        cursor.execute("""
            SELECT schemaname, tablename, indexname, indexdef
            FROM pg_indexes
            WHERE tablename IN ('checker_component', 'checker_locationgroup')
            ORDER BY tablename, indexname
        """)
        
        print("\n📋 Current indexes:")
        for row in cursor.fetchall():
            print(f"  - {row[1]}.{row[2]}")

def optimize_technology_queries():
    """Show how to optimize the queries in the code."""
    print("\n💡 Query Optimization Recommendations:")
    
    print("""
    Replace slow queries like:
    ❌ Component.objects.filter(technology__icontains='DSR')
    
    With optimized versions:
    ✅ Component.objects.filter(technology__iexact='DSR')
    ✅ LocationGroup.objects.filter(technologies__contains=['DSR'])
    
    For case-insensitive searches, use the indexes:
    ✅ Component.objects.extra(where=["UPPER(technology) = UPPER(%s)"], params=['DSR'])
    """)

def create_materialized_view():
    """Create a materialized view for technology summaries."""
    print("\n🎯 Creating materialized view for technology summaries...")
    
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS technology_summary AS
                SELECT 
                    UPPER(technology) as technology_normalized,
                    technology as technology_original,
                    COUNT(DISTINCT location) as location_count,
                    COUNT(*) as component_count,
                    SUM(CASE WHEN derated_capacity_mw IS NOT NULL 
                        THEN derated_capacity_mw ELSE 0 END) as total_capacity,
                    COUNT(DISTINCT company_name) as company_count,
                    MAX(delivery_year) as latest_year,
                    array_agg(DISTINCT delivery_year ORDER BY delivery_year DESC) as years
                FROM checker_component
                WHERE technology IS NOT NULL
                GROUP BY technology
            """)
            
            # Create index on the materialized view
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tech_summary_normalized 
                ON technology_summary (technology_normalized)
            """)
            
            print("✅ Created technology_summary materialized view")
            
            # Refresh it
            cursor.execute("REFRESH MATERIALIZED VIEW technology_summary")
            print("✅ Refreshed materialized view with current data")
            
        except Exception as e:
            print(f"⚠️  Materialized view error: {e}")

def test_performance():
    """Test the performance improvements."""
    print("\n🧪 Testing performance improvements...")
    
    from checker.models import Component, LocationGroup
    import time
    
    technologies = ['DSR', 'Battery', 'Solar', 'Wind']
    
    for tech in technologies:
        # Test old approach
        start = time.time()
        count = Component.objects.filter(technology__icontains=tech).count()
        old_time = time.time() - start
        
        # Test new approach with exact match
        start = time.time()
        count_exact = Component.objects.filter(technology__iexact=tech).count()
        new_time = time.time() - start
        
        # Test LocationGroup approach
        start = time.time()
        lg_count = LocationGroup.objects.filter(technologies__contains=[tech]).count()
        lg_time = time.time() - start
        
        print(f"\n{tech} Technology:")
        print(f"  Old query (icontains): {old_time:.3f}s ({count} results)")
        print(f"  New query (iexact): {new_time:.3f}s ({count_exact} results)")
        print(f"  LocationGroup query: {lg_time:.3f}s ({lg_count} locations)")
        print(f"  Speed improvement: {old_time/new_time:.1f}x faster")

if __name__ == "__main__":
    print("🔧 TECHNOLOGY PERFORMANCE FIX")
    print("=" * 50)
    
    create_performance_indexes()
    analyze_current_queries()
    create_materialized_view()
    optimize_technology_queries()
    test_performance()
    
    print("\n✅ Performance optimizations complete!")
    print("\nNext steps:")
    print("1. Run migrations if needed")
    print("2. Update views to use optimized queries")
    print("3. Clear Redis cache to see improvements")
    print("4. Monitor query performance in production")