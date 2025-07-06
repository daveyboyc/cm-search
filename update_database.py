#!/usr/bin/env python3
"""
Consolidated script for updating the CMR database.
This script replaces multiple redundant management commands.
"""
import os
import sys
import time
import argparse
import logging
import django
from django.core.management import call_command

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('update_log.txt')
    ]
)
logger = logging.getLogger(__name__)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

def crawl_to_database(args):
    """Import data directly to the database"""
    logger.info("=== STEP 1: CRAWLING COMPONENTS TO DATABASE ===")
    
    start_time = time.time()
    try:
        # Call the Django management command
        cmd_args = []
        if args.import_limit:
            cmd_args.extend(['--limit', str(args.import_limit)])
        
        if args.import_src:
            cmd_args.extend(['--source', args.import_src])
            
        logger.info(f"Running crawl_to_database command with args: {cmd_args}")
        call_command('crawl_to_database', *cmd_args)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Data import completed in {elapsed_time:.2f}s")
        return True
        
    except Exception as e:
        logger.error(f"Error during data import: {e}")
        return False

def geocode_components(args):
    """Geocode components that don't have coordinates"""
    logger.info("=== STEP 2: GEOCODING COMPONENTS ===")
    
    start_time = time.time()
    try:
        # Call the Django management command
        cmd_args = []
        if args.geocode_limit:
            cmd_args.extend(['--limit', str(args.geocode_limit)])
            
        logger.info(f"Running geocode_components command with args: {cmd_args}")
        call_command('geocode_components', *cmd_args)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Geocoding completed in {elapsed_time:.2f}s")
        return True
        
    except Exception as e:
        logger.error(f"Error during geocoding: {e}")
        return False

def rebuild_search_index():
    """Rebuild the full-text search index"""
    logger.info("=== STEP 3: REBUILDING SEARCH INDEX ===")
    
    start_time = time.time()
    try:
        # Call the Django management command
        logger.info("Running rebuild_search_index command")
        call_command('rebuild_search_index')
        
        elapsed_time = time.time() - start_time
        logger.info(f"Search index rebuild completed in {elapsed_time:.2f}s")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding search index: {e}")
        return False

def rebuild_redis_caches():
    """Rebuild all Redis caches"""
    logger.info("=== STEP 4: REBUILDING REDIS CACHES ===")
    
    start_time = time.time()
    try:
        # Call the required Django management commands
        
        # 1. Build location mapping
        logger.info("Building location mapping")
        call_command('build_location_mapping')
        
        # 2. Build map cache
        logger.info("Building map cache")
        call_command('build_map_cache')
        
        # 3. Build location groups cache
        logger.info("Building location groups cache")
        call_command('build_location_groups_cache')
        
        # 4. Verify cache status
        logger.info("Checking cache status")
        call_command('check_cache_status')
        
        elapsed_time = time.time() - start_time
        logger.info(f"Redis caches rebuild completed in {elapsed_time:.2f}s")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding Redis caches: {e}")
        return False

def update_database(args):
    """Run the complete database update process"""
    total_start_time = time.time()
    results = {}
    
    # Step 1: Import data to database
    if not args.skip_import:
        import_result = crawl_to_database(args)
        results["data_import"] = "Success" if import_result else "Failed"
    else:
        logger.info("Skipping data import")
        results["data_import"] = "Skipped"
    
    # Step 2: Geocode components
    if not args.skip_geocode:
        geocode_result = geocode_components(args)
        results["geocoding"] = "Success" if geocode_result else "Failed"
    else:
        logger.info("Skipping geocoding")
        results["geocoding"] = "Skipped"
    
    # Step 3: Rebuild search index
    if not args.skip_index:
        index_result = rebuild_search_index()
        results["search_index"] = "Success" if index_result else "Failed"
    else:
        logger.info("Skipping search index rebuild")
        results["search_index"] = "Skipped"
    
    # Step 4: Rebuild Redis caches
    if not args.skip_cache:
        cache_result = rebuild_redis_caches()
        results["redis_caches"] = "Success" if cache_result else "Failed"
    else:
        logger.info("Skipping Redis caches rebuild")
        results["redis_caches"] = "Skipped"
    
    # Print summary
    total_time = time.time() - total_start_time
    logger.info("===== UPDATE PROCESS COMPLETED =====")
    logger.info(f"Total time: {total_time:.2f}s")
    
    for step, status in results.items():
        logger.info(f"{step}: {status}")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update CMR database")
    
    # Step control arguments
    parser.add_argument('--skip-import', action='store_true', help="Skip data import")
    parser.add_argument('--skip-geocode', action='store_true', help="Skip geocoding")
    parser.add_argument('--skip-index', action='store_true', help="Skip search index rebuild")
    parser.add_argument('--skip-cache', action='store_true', help="Skip Redis caches rebuild")
    
    # Import options
    parser.add_argument('--import-src', help="Data source for import")
    parser.add_argument('--import-limit', type=int, help="Max components to import")
    
    # Geocode options
    parser.add_argument('--geocode-limit', type=int, default=500, help="Max components to geocode")
    
    args = parser.parse_args()
    
    # Run the update process
    update_database(args)