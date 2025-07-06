#!/usr/bin/env python3
"""
Hybrid optimization using both Supabase PostgreSQL and Redis.
This script implements:
1. PostgreSQL materialized views and full-text search
2. Redis caching for pre-computed search results and map data
3. Smart cache invalidation and refresh strategies
"""
import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
import django
from django.core.cache import cache

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

# Import Supabase connection
from supabase_integration import get_db_connection

def setup_postgresql_optimizations():
    """
    Set up PostgreSQL optimizations including:
    - Full-text search indexes
    - Materialized views
    - Database functions
    """
    logger.info("Setting up PostgreSQL optimizations...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Step 1: Add search_vector column if it doesn't exist
            logger.info("Creating search vector column and index...")
            cursor.execute("""
            ALTER TABLE checker_component ADD COLUMN IF NOT EXISTS search_vector tsvector;
            CREATE INDEX IF NOT EXISTS components_search_idx ON checker_component USING GIN(search_vector);
            """)
            
            # Step 2: Create trigger for automatic updates
            logger.info("Creating search vector update trigger...")
            cursor.execute("""
            CREATE OR REPLACE FUNCTION component_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector = 
                    setweight(to_tsvector('english', COALESCE(NEW.company_name, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.county, '')), 'B') ||
                    setweight(to_tsvector('english', COALESCE(NEW.outward_code, '')), 'B') ||
                    setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
                    setweight(to_tsvector('english', COALESCE(NEW.technology, '')), 'C') ||
                    setweight(to_tsvector('english', COALESCE(NEW.cmu_id, '')), 'D') ||
                    setweight(to_tsvector('english', COALESCE(NEW.auction_name, '')), 'D') ||
                    setweight(to_tsvector('english', COALESCE(NEW.delivery_year, '')), 'D');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS component_search_trigger ON checker_component;
            
            CREATE TRIGGER component_search_trigger
            BEFORE INSERT OR UPDATE ON checker_component
            FOR EACH ROW
            EXECUTE FUNCTION component_search_vector_update();
            """)
            
            # Step 3: Create materialized views for common queries
            logger.info("Creating materialized views...")
            
            # Technology statistics view
            cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_technology_stats AS
            SELECT technology, COUNT(*) as component_count,
                   COUNT(DISTINCT company_name) as company_count,
                   SUM(derated_capacity_mw) as total_capacity
            FROM checker_component
            WHERE technology IS NOT NULL AND technology != ''
            GROUP BY technology
            ORDER BY component_count DESC;
            """)
            
            # Company statistics view
            cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_company_stats AS
            SELECT company_name, COUNT(*) as component_count,
                   COUNT(DISTINCT technology) as technology_count,
                   SUM(derated_capacity_mw) as total_capacity
            FROM checker_component
            WHERE company_name IS NOT NULL AND company_name != ''
            GROUP BY company_name
            ORDER BY component_count DESC;
            """)
            
            # Location groups view
            cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_location_groups AS
            SELECT location, 
                   description,
                   array_agg(DISTINCT cmu_id) as cmu_ids,
                   array_agg(DISTINCT auction_name) as auction_names,
                   bool_or(delivery_year::numeric >= 2024) as active_status,
                   COUNT(*) as component_count
            FROM checker_component
            WHERE location IS NOT NULL AND location != ''
            GROUP BY location, description;
            """)
            
            # Map data view
            cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_map_data AS
            SELECT id, location, technology, company_name, latitude, longitude, derated_capacity_mw, 
                   delivery_year, 'checker_component' as source_table
            FROM checker_component
            WHERE geocoded = true AND latitude IS NOT NULL AND longitude IS NOT NULL;
            """)
            
            # Step 4: Create function to refresh materialized views
            logger.info("Creating refresh function...")
            cursor.execute("""
            CREATE OR REPLACE FUNCTION refresh_materialized_views() RETURNS void AS $$
            BEGIN
              REFRESH MATERIALIZED VIEW CONCURRENTLY mv_technology_stats;
              REFRESH MATERIALIZED VIEW CONCURRENTLY mv_company_stats;
              REFRESH MATERIALIZED VIEW CONCURRENTLY mv_location_groups;
              REFRESH MATERIALIZED VIEW CONCURRENTLY mv_map_data;
            END;
            $$ LANGUAGE plpgsql;
            """)
            
            # Step 5: Create helper function for component search
            logger.info("Creating search helper functions...")
            cursor.execute("""
            CREATE OR REPLACE FUNCTION search_components(search_query text, max_results integer DEFAULT 1000)
            RETURNS TABLE(
                id integer,
                cmu_id text,
                company_name text,
                location text,
                technology text,
                description text,
                auction_name text,
                delivery_year text,
                derated_capacity_mw numeric,
                rank float4
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT c.id, c.cmu_id, c.company_name, c.location, c.technology, 
                       c.description, c.auction_name, c.delivery_year, 
                       c.derated_capacity_mw,
                       ts_rank(c.search_vector, websearch_to_tsquery('english', search_query)) as rank
                FROM checker_component c
                WHERE c.search_vector @@ websearch_to_tsquery('english', search_query)
                ORDER BY rank DESC
                LIMIT max_results;
            END;
            $$ LANGUAGE plpgsql;
            """)
            
            # Commit all changes
            conn.commit()
            
    logger.info("PostgreSQL optimizations completed successfully!")

def update_search_vectors():
    """Update search vectors for existing records"""
    logger.info("Updating search vectors for existing records...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            UPDATE checker_component
            SET search_vector = 
                setweight(to_tsvector('english', COALESCE(company_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(location, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(county, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(outward_code, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(technology, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(cmu_id, '')), 'D') ||
                setweight(to_tsvector('english', COALESCE(auction_name, '')), 'D') ||
                setweight(to_tsvector('english', COALESCE(delivery_year, '')), 'D')
            WHERE search_vector IS NULL
            """)
            
            updated = cursor.rowcount
            conn.commit()
            
    logger.info(f"Updated search vectors for {updated} records")
    return updated

def refresh_materialized_views():
    """Refresh all materialized views"""
    logger.info("Refreshing materialized views...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT refresh_materialized_views()")
            conn.commit()
            
    logger.info("Materialized views refreshed successfully")

def build_redis_caches():
    """
    Build Redis caches for:
    1. Map data by technology
    2. Common search terms
    3. Technology and company statistics
    
    This reduces database load and egress costs while providing faster responses.
    """
    logger.info("Building Redis caches...")
    
    # Step 1: Cache map data by technology
    cache_map_data_by_technology()
    
    # Step 2: Cache technology statistics
    cache_technology_stats()
    
    # Step 3: Cache company statistics
    cache_company_stats()
    
    # Step 4: Pre-cache common searches
    cache_common_searches()
    
    logger.info("Redis caches built successfully!")

def cache_map_data_by_technology():
    """Cache map data grouped by technology in Redis"""
    logger.info("Caching map data by technology...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Get all distinct technologies
            cursor.execute("SELECT DISTINCT technology FROM checker_component WHERE technology IS NOT NULL AND technology != ''")
            technologies = [row[0] for row in cursor.fetchall()]
            
            # Get all map data
            cursor.execute("""
            SELECT id, location, technology, company_name, latitude, longitude, 
                   derated_capacity_mw, delivery_year
            FROM mv_map_data
            """)
            
            all_map_data = cursor.fetchall()
            
            # Group data by technology
            tech_map_data = {}
            for row in all_map_data:
                tech = row[2]  # technology is at index 2
                if tech not in tech_map_data:
                    tech_map_data[tech] = []
                
                tech_map_data[tech].append({
                    'id': row[0],
                    'location': row[1],
                    'technology': row[2],
                    'company_name': row[3],
                    'latitude': float(row[4]) if row[4] else None,
                    'longitude': float(row[5]) if row[5] else None,
                    'derated_capacity_mw': float(row[6]) if row[6] else None,
                    'delivery_year': row[7]
                })
    
    # Cache each technology's map data
    for tech, data in tech_map_data.items():
        cache_key = f"map_data:tech:{tech}"
        logger.info(f"Caching {len(data)} map points for technology: {tech}")
        cache.set(cache_key, json.dumps(data), timeout=None)  # No expiration
    
    # Cache all map data
    all_data = []
    for tech_data in tech_map_data.values():
        all_data.extend(tech_data)
    
    cache.set("map_data:all", json.dumps(all_data), timeout=None)
    logger.info(f"Cached total of {len(all_data)} map points across {len(tech_map_data)} technologies")

def cache_technology_stats():
    """Cache technology statistics in Redis"""
    logger.info("Caching technology statistics...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT technology, component_count, company_count, total_capacity
            FROM mv_technology_stats
            ORDER BY component_count DESC
            """)
            
            stats = []
            for row in cursor.fetchall():
                stats.append({
                    'technology': row[0],
                    'component_count': row[1],
                    'company_count': row[2],
                    'total_capacity': float(row[3]) if row[3] else 0
                })
    
    cache.set("stats:technology", json.dumps(stats), timeout=None)
    logger.info(f"Cached statistics for {len(stats)} technologies")

def cache_company_stats():
    """Cache company statistics in Redis"""
    logger.info("Caching company statistics...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT company_name, component_count, technology_count, total_capacity
            FROM mv_company_stats
            ORDER BY component_count DESC
            LIMIT 100  # Cache only top 100 companies to reduce memory usage
            """)
            
            stats = []
            for row in cursor.fetchall():
                stats.append({
                    'company_name': row[0],
                    'component_count': row[1],
                    'technology_count': row[2],
                    'total_capacity': float(row[3]) if row[3] else 0
                })
    
    cache.set("stats:company", json.dumps(stats), timeout=None)
    logger.info(f"Cached statistics for {len(stats)} companies")

def cache_common_searches():
    """Pre-cache results for common search terms to reduce database load"""
    logger.info("Pre-caching common search terms...")
    
    # List of common search terms (based on your most frequent queries)
    common_searches = [
        "vital", "energy", "battery", "london", "manchester", 
        "solar", "wind", "hydro", "gas", "biomass"
    ]
    
    for term in common_searches:
        logger.info(f"Caching search results for term: '{term}'")
        
        # Use the database function for search
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM search_components(%s, 200)", (term,))
                results = []
                
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'cmu_id': row[1],
                        'company_name': row[2],
                        'location': row[3],
                        'technology': row[4],
                        'description': row[5],
                        'auction_name': row[6],
                        'delivery_year': row[7],
                        'derated_capacity_mw': float(row[8]) if row[8] else None,
                        'rank': float(row[9]) if row[9] else 0
                    })
        
        # Create a cache key for this search
        search_key = f"search:{hashlib.md5(term.encode('utf-8')).hexdigest()}"
        
        # Cache the search with expiration (1 day)
        cache.set(search_key, json.dumps({
            'query': term,
            'results': results,
            'total_count': len(results),
            'cached_at': datetime.now().isoformat(),
            'cache_version': 1
        }), timeout=3600)  # 1 hour - reduce network egress
        
        logger.info(f"Cached {len(results)} results for search term: '{term}'")

def optimize_database():
    """Run database optimization commands (VACUUM, ANALYZE, etc.)"""
    logger.info("Running database optimizations...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Analyze tables to gather statistics for query planner
            cursor.execute("ANALYZE checker_component")
            
            # Vacuum to reclaim space and update statistics
            cursor.execute("VACUUM ANALYZE checker_component")
            
            conn.commit()
    
    logger.info("Database optimizations completed")

def run_hybrid_optimization():
    """Run the complete hybrid optimization process"""
    start_time = time.time()
    
    # Step 1: Set up PostgreSQL optimizations
    setup_postgresql_optimizations()
    
    # Step 2: Update search vectors for existing records
    update_search_vectors()
    
    # Step 3: Refresh materialized views
    refresh_materialized_views()
    
    # Step 4: Build Redis caches
    build_redis_caches()
    
    # Step 5: Optimize database
    optimize_database()
    
    elapsed_time = time.time() - start_time
    logger.info(f"Hybrid optimization completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid optimization using PostgreSQL and Redis")
    parser.add_argument('--skip-postgres', action='store_true', help="Skip PostgreSQL optimizations")
    parser.add_argument('--skip-redis', action='store_true', help="Skip Redis cache building")
    parser.add_argument('--refresh-views', action='store_true', help="Only refresh materialized views")
    parser.add_argument('--update-vectors', action='store_true', help="Only update search vectors")
    
    args = parser.parse_args()
    
    if args.refresh_views:
        refresh_materialized_views()
    elif args.update_vectors:
        update_search_vectors()
    else:
        # Full optimization process
        if not args.skip_postgres:
            setup_postgresql_optimizations()
            update_search_vectors()
            refresh_materialized_views()
            optimize_database()
            
        if not args.skip_redis:
            build_redis_caches()