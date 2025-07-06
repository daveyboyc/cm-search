#!/usr/bin/env python3
"""
Complete update script that:
1. Imports components data to Supabase
2. Updates search vectors for full-text search
3. Refreshes materialized views
4. Builds Redis caches for fast access
5. Verifies the update process
"""
import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hybrid_update_log.txt')
    ]
)
logger = logging.getLogger(__name__)

def import_data_to_supabase(args):
    """Import data to Supabase PostgreSQL database"""
    logger.info("=== STEP 1: IMPORTING DATA TO SUPABASE ===")
    import psycopg2
    from psycopg2.extras import execute_values
    
    try:
        from supabase_integration import get_db_connection
        
        # Process the data source
        source_file = args.import_src
        if not source_file or not os.path.exists(source_file):
            logger.error(f"Data source file not found: {source_file}")
            return False
        
        # Load the data
        logger.info(f"Loading data from: {source_file}")
        with open(source_file, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            components = data
        elif isinstance(data, dict) and 'components' in data:
            components = data['components']
        else:
            logger.error("Invalid data format. Expected list or dict with 'components' key.")
            return False
        
        # Apply limit if specified
        if args.import_limit and args.import_limit > 0:
            components = components[:args.import_limit]
        
        logger.info(f"Importing {len(components)} components to Supabase")
        
        # Connect to database
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Prepare data for import
                values = []
                columns = [
                    'cmu_id', 'company_name', 'location', 'description', 
                    'technology', 'auction_name', 'delivery_year', 'status',
                    'derated_capacity_mw'
                ]
                
                for comp in components:
                    # Map fields from various possible formats
                    cmu_id = comp.get('cmu_id', comp.get('CMU ID', ''))
                    company_name = comp.get('company_name', comp.get('Company Name', ''))
                    location = comp.get('location', comp.get('Location and Post Code', ''))
                    description = comp.get('description', comp.get('Description of CMU Components', ''))
                    technology = comp.get('technology', comp.get('Generating Technology Class', ''))
                    auction_name = comp.get('auction_name', comp.get('Auction Name', ''))
                    delivery_year = comp.get('delivery_year', comp.get('Delivery Year', ''))
                    status = comp.get('status', comp.get('Status', ''))
                    
                    # Handle capacity in different formats
                    derated_capacity = None
                    capacity_fields = ['derated_capacity_mw', 'derated_capacity', 'De-Rated Capacity']
                    for field in capacity_fields:
                        if field in comp and comp[field] is not None:
                            try:
                                derated_capacity = float(comp[field])
                                break
                            except (ValueError, TypeError):
                                pass
                    
                    values.append((
                        cmu_id, company_name, location, description,
                        technology, auction_name, delivery_year, status,
                        derated_capacity
                    ))
                
                # Insert data in batches
                batch_size = 100
                for i in range(0, len(values), batch_size):
                    batch = values[i:i+batch_size]
                    
                    try:
                        # Create the SQL for the insert
                        sql = """
                        INSERT INTO checker_component (
                            cmu_id, company_name, location, description, 
                            technology, auction_name, delivery_year, status,
                            derated_capacity_mw
                        ) VALUES %s
                        ON CONFLICT (cmu_id) 
                        DO UPDATE SET 
                            company_name = EXCLUDED.company_name,
                            location = EXCLUDED.location,
                            description = EXCLUDED.description,
                            technology = EXCLUDED.technology,
                            auction_name = EXCLUDED.auction_name,
                            delivery_year = EXCLUDED.delivery_year,
                            status = EXCLUDED.status,
                            derated_capacity_mw = EXCLUDED.derated_capacity_mw
                        """
                        
                        # Execute the batch insert
                        execute_values(cursor, sql, batch)
                        conn.commit()
                        
                        logger.info(f"Imported batch {i//batch_size + 1}/{(len(values) + batch_size - 1)//batch_size}: {len(batch)} components")
                        
                    except Exception as e:
                        logger.error(f"Error importing batch: {e}")
                        conn.rollback()
                        
                # Report success
                logger.info(f"Successfully imported {len(values)} components to Supabase")
        
        return True
        
    except Exception as e:
        logger.error(f"Error importing data to Supabase: {e}")
        return False

def update_search_vectors():
    """Update search vectors for full-text search"""
    logger.info("=== STEP 2: UPDATING SEARCH VECTORS ===")
    
    try:
        # Import the function from hybrid_optimization.py
        from hybrid_optimization import update_search_vectors
        
        # Run the function
        updated = update_search_vectors()
        
        logger.info(f"Updated search vectors for {updated} components")
        return True
        
    except Exception as e:
        logger.error(f"Error updating search vectors: {e}")
        return False

def refresh_materialized_views():
    """Refresh materialized views"""
    logger.info("=== STEP 3: REFRESHING MATERIALIZED VIEWS ===")
    
    try:
        # Import the function from hybrid_optimization.py
        from hybrid_optimization import refresh_materialized_views
        
        # Run the function
        refresh_materialized_views()
        
        logger.info("Successfully refreshed materialized views")
        return True
        
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")
        return False

def build_redis_caches():
    """Build Redis caches for fast access"""
    logger.info("=== STEP 4: BUILDING REDIS CACHES ===")
    
    try:
        # Import the function from hybrid_optimization.py
        from hybrid_optimization import build_redis_caches
        
        # Run the function
        build_redis_caches()
        
        logger.info("Successfully built Redis caches")
        return True
        
    except Exception as e:
        logger.error(f"Error building Redis caches: {e}")
        return False

def geocode_components(args):
    """Geocode components that don't have coordinates"""
    logger.info("=== STEP 5: GEOCODING COMPONENTS ===")
    
    try:
        from supabase_integration import get_db_connection
        import requests
        
        # Get Google Maps API key
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
        if not api_key:
            logger.error("GOOGLE_MAPS_API_KEY not found in environment variables")
            return False
        
        # Get components that need geocoding
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                SELECT id, location
                FROM checker_component
                WHERE geocoded = false AND location IS NOT NULL AND location != ''
                LIMIT %s
                """, (args.geocode_limit,))
                
                components = cursor.fetchall()
        
        logger.info(f"Found {len(components)} components to geocode")
        
        # Geocode each component
        geocoded = 0
        errors = 0
        
        for comp_id, location in components:
            if not location:
                continue
                
            try:
                # Call Google Maps Geocoding API
                response = requests.get(
                    'https://maps.googleapis.com/maps/api/geocode/json',
                    params={
                        'address': location,
                        'key': api_key,
                        'region': 'uk'
                    }
                )
                
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    # Extract coordinates
                    location_data = data['results'][0]['geometry']['location']
                    latitude = location_data['lat']
                    longitude = location_data['lng']
                    
                    # Update component with coordinates
                    with get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                            UPDATE checker_component
                            SET latitude = %s, longitude = %s, geocoded = true
                            WHERE id = %s
                            """, (latitude, longitude, comp_id))
                            conn.commit()
                    
                    geocoded += 1
                    logger.info(f"Geocoded component {comp_id}: ({latitude}, {longitude})")
                else:
                    logger.warning(f"Failed to geocode component {comp_id}: {data.get('status', 'Unknown error')}")
                    errors += 1
                
                # Sleep to avoid hitting API rate limits
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error geocoding component {comp_id}: {e}")
                errors += 1
        
        logger.info(f"Geocoding completed: {geocoded} successful, {errors} errors")
        
        # Refresh map data view if components were geocoded
        if geocoded > 0:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("REFRESH MATERIALIZED VIEW mv_map_data")
                    conn.commit()
            
            logger.info("Refreshed map data view with new geocoded components")
        
        return True
        
    except Exception as e:
        logger.error(f"Error geocoding components: {e}")
        return False

def verify_update(args):
    """Verify the update process"""
    logger.info("=== STEP 6: VERIFYING UPDATE ===")
    
    try:
        from supabase_integration import get_db_connection
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check component count
                cursor.execute("SELECT COUNT(*) FROM checker_component")
                component_count = cursor.fetchone()[0]
                
                # Check geocoded component count
                cursor.execute("SELECT COUNT(*) FROM checker_component WHERE geocoded = true")
                geocoded_count = cursor.fetchone()[0]
                
                # Check materialized views
                cursor.execute("SELECT COUNT(*) FROM mv_technology_stats")
                tech_stats_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM mv_company_stats")
                company_stats_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM mv_location_groups")
                location_groups_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM mv_map_data")
                map_data_count = cursor.fetchone()[0]
        
        # Check Redis cache status
        from django.core.cache import cache
        cache_keys = [
            "map_data:all",
            "stats:technology",
            "stats:company"
        ]
        
        redis_cache_status = {}
        for key in cache_keys:
            data = cache.get(key)
            if data:
                try:
                    json_data = json.loads(data)
                    item_count = len(json_data)
                    redis_cache_status[key] = f"Cached ({item_count} items)"
                except:
                    redis_cache_status[key] = "Cached (invalid JSON)"
            else:
                redis_cache_status[key] = "Not cached"
        
        # Print verification report
        logger.info("\n=== UPDATE VERIFICATION REPORT ===")
        logger.info(f"Total components: {component_count}")
        logger.info(f"Geocoded components: {geocoded_count} ({geocoded_count/component_count*100:.1f}%)")
        logger.info("\nMaterialized Views:")
        logger.info(f"  Technology stats: {tech_stats_count} records")
        logger.info(f"  Company stats: {company_stats_count} records")
        logger.info(f"  Location groups: {location_groups_count} records")
        logger.info(f"  Map data: {map_data_count} records")
        logger.info("\nRedis Cache Status:")
        for key, status in redis_cache_status.items():
            logger.info(f"  {key}: {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying update: {e}")
        return False

def run_hybrid_update(args):
    """Run the complete hybrid update process"""
    start_time = time.time()
    results = {}
    
    # Step 1: Import data to Supabase
    if not args.skip_import:
        import_result = import_data_to_supabase(args)
        results["data_import"] = "Success" if import_result else "Failed"
    else:
        logger.info("Skipping data import")
        results["data_import"] = "Skipped"
    
    # Step 2: Update search vectors
    if not args.skip_vectors:
        vectors_result = update_search_vectors()
        results["search_vectors"] = "Success" if vectors_result else "Failed"
    else:
        logger.info("Skipping search vector update")
        results["search_vectors"] = "Skipped"
    
    # Step 3: Refresh materialized views
    if not args.skip_views:
        views_result = refresh_materialized_views()
        results["materialized_views"] = "Success" if views_result else "Failed"
    else:
        logger.info("Skipping materialized view refresh")
        results["materialized_views"] = "Skipped"
    
    # Step 4: Build Redis caches
    if not args.skip_redis:
        redis_result = build_redis_caches()
        results["redis_caches"] = "Success" if redis_result else "Failed"
    else:
        logger.info("Skipping Redis cache building")
        results["redis_caches"] = "Skipped"
    
    # Step 5: Geocode components
    if not args.skip_geocode:
        geocode_result = geocode_components(args)
        results["geocoding"] = "Success" if geocode_result else "Failed"
    else:
        logger.info("Skipping geocoding")
        results["geocoding"] = "Skipped"
    
    # Step 6: Verify update
    if not args.skip_verify:
        verify_result = verify_update(args)
        results["verification"] = "Success" if verify_result else "Failed"
    else:
        logger.info("Skipping verification")
        results["verification"] = "Skipped"
    
    # Print summary
    total_time = time.time() - start_time
    logger.info("\n===== HYBRID UPDATE COMPLETED =====")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info("Results:")
    
    for step, status in results.items():
        logger.info(f"  {step}: {status}")
    
    # Save update log
    update_log = {
        "timestamp": datetime.now().isoformat(),
        "duration": total_time,
        "results": results
    }
    
    with open('hybrid_update_history.json', 'a') as f:
        f.write(json.dumps(update_log) + "\n")
    
    return all(status == "Success" for status in results.values() if status != "Skipped")

if __name__ == "__main__":
    # Configure argument parser
    parser = argparse.ArgumentParser(description="Hybrid update process for CMR application")
    
    # Step control arguments
    parser.add_argument('--skip-import', action='store_true', help="Skip data import")
    parser.add_argument('--skip-vectors', action='store_true', help="Skip search vector update")
    parser.add_argument('--skip-views', action='store_true', help="Skip materialized view refresh")
    parser.add_argument('--skip-redis', action='store_true', help="Skip Redis cache building")
    parser.add_argument('--skip-geocode', action='store_true', help="Skip geocoding")
    parser.add_argument('--skip-verify', action='store_true', help="Skip verification")
    
    # Import options
    parser.add_argument('--import-src', help="Data source file for import")
    parser.add_argument('--import-limit', type=int, help="Max components to import")
    
    # Geocode options
    parser.add_argument('--geocode-limit', type=int, default=100, help="Max components to geocode")
    
    args = parser.parse_args()
    
    # Run the update process
    success = run_hybrid_update(args)
    sys.exit(0 if success else 1)