#!/usr/bin/env python3
"""
Update script that uses Supabase instead of Django models for better performance.
This script replaces the multiple management commands with a streamlined workflow.
"""
import os
import sys
import time
import json
import logging
import argparse
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('update_log.txt')
    ]
)
logger = logging.getLogger(__name__)

# Import Supabase integration
try:
    from supabase_integration import (
        get_supabase_client, 
        import_components_to_supabase,
        build_location_groups_in_supabase,
        refresh_materialized_views
    )
except ImportError:
    logger.error("Failed to import supabase_integration. Please make sure it's installed.")
    sys.exit(1)

# Load environment variables
load_dotenv()

def crawl_and_import_to_supabase(api_url=None, limit=None):
    """
    Crawl component data from API and import directly to Supabase.
    
    Args:
        api_url (str): URL of the API to crawl
        limit (int): Maximum number of components to crawl
        
    Returns:
        dict: Statistics about the operation
    """
    import requests
    from tqdm import tqdm
    
    logger.info("Starting data crawl and import to Supabase")
    stats = {"crawled": 0, "imported": 0, "errors": 0}
    
    # Use default API URL if not provided
    api_url = api_url or os.getenv("COMPONENTS_API_URL")
    if not api_url:
        logger.error("API URL not provided and not found in environment")
        return stats
    
    try:
        # Fetch data from API
        logger.info(f"Fetching data from {api_url}")
        response = requests.get(api_url)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        components = data.get("components", [])
        
        # Apply limit if specified
        if limit and limit > 0:
            components = components[:limit]
        
        stats["crawled"] = len(components)
        logger.info(f"Crawled {stats['crawled']} components")
        
        # Import to Supabase
        import_stats = import_components_to_supabase(components)
        
        # Update stats
        stats["imported"] = import_stats["imported"]
        stats["errors"] = import_stats["errors"]
        stats["elapsed_time"] = import_stats.get("elapsed_time", 0)
        
    except Exception as e:
        logger.error(f"Error during crawl and import: {e}")
        stats["errors"] += 1
    
    return stats

def geocode_components_via_supabase(limit=500):
    """
    Geocode components directly in Supabase using PostgreSQL function.
    
    Args:
        limit (int): Maximum number of components to geocode
        
    Returns:
        dict: Statistics about the operation
    """
    logger.info(f"Starting geocoding of up to {limit} components")
    start_time = time.time()
    stats = {"processed": 0, "geocoded": 0, "errors": 0}
    
    try:
        supabase = get_supabase_client()
        
        # Call PostgreSQL function to geocode components
        # This assumes you've created the function in your Supabase database
        result = supabase.rpc(
            'geocode_components', 
            {"max_components": limit}
        ).execute()
        
        # Process result
        if hasattr(result, 'data'):
            stats["processed"] = result.data.get("processed", 0)
            stats["geocoded"] = result.data.get("geocoded", 0)
            stats["errors"] = result.data.get("errors", 0)
        
    except Exception as e:
        logger.error(f"Error during geocoding: {e}")
        stats["errors"] += 1
    
    stats["elapsed_time"] = time.time() - start_time
    logger.info(f"Geocoding completed in {stats['elapsed_time']:.2f}s. "
                f"Processed: {stats['processed']}, "
                f"Geocoded: {stats['geocoded']}, "
                f"Errors: {stats['errors']}")
    
    return stats

def rebuild_search_index():
    """
    Rebuild the PostgreSQL full-text search index in Supabase.
    
    Returns:
        dict: Statistics about the operation
    """
    logger.info("Rebuilding search index")
    start_time = time.time()
    stats = {"processed": 0, "errors": 0}
    
    try:
        supabase = get_supabase_client()
        
        # Call PostgreSQL function to rebuild search index
        result = supabase.rpc('rebuild_search_index', {}).execute()
        
        if hasattr(result, 'data'):
            stats["processed"] = result.data.get("processed", 0)
    
    except Exception as e:
        logger.error(f"Error rebuilding search index: {e}")
        stats["errors"] += 1
    
    stats["elapsed_time"] = time.time() - start_time
    logger.info(f"Search index rebuild completed in {stats['elapsed_time']:.2f}s")
    
    return stats

def update_with_supabase(args):
    """
    Run the complete update process using Supabase.
    
    Args:
        args: Command line arguments
    """
    total_start_time = time.time()
    all_stats = {}
    
    # Step 1: Crawl and import data to Supabase
    if not args.skip_import:
        logger.info("=== STEP 1: CRAWLING AND IMPORTING DATA ===")
        import_stats = crawl_and_import_to_supabase(
            api_url=args.api_url,
            limit=args.import_limit
        )
        all_stats["import"] = import_stats
    else:
        logger.info("Skipping data import")
    
    # Step 2: Geocode components
    if not args.skip_geocode:
        logger.info("=== STEP 2: GEOCODING COMPONENTS ===")
        geocode_stats = geocode_components_via_supabase(limit=args.geocode_limit)
        all_stats["geocode"] = geocode_stats
    else:
        logger.info("Skipping geocoding")
    
    # Step 3: Rebuild search index
    if not args.skip_index:
        logger.info("=== STEP 3: REBUILDING SEARCH INDEX ===")
        index_stats = rebuild_search_index()
        all_stats["index"] = index_stats
    else:
        logger.info("Skipping search index rebuild")
    
    # Step 4: Build location groups
    if not args.skip_location_groups:
        logger.info("=== STEP 4: BUILDING LOCATION GROUPS ===")
        groups_stats = build_location_groups_in_supabase()
        all_stats["location_groups"] = groups_stats
    else:
        logger.info("Skipping location groups build")
    
    # Step 5: Refresh materialized views
    if not args.skip_views:
        logger.info("=== STEP 5: REFRESHING MATERIALIZED VIEWS ===")
        refresh_result = refresh_materialized_views()
        all_stats["refresh_views"] = {"success": refresh_result}
    else:
        logger.info("Skipping materialized views refresh")
    
    # Calculate total time
    total_time = time.time() - total_start_time
    all_stats["total_time"] = total_time
    
    logger.info(f"=== UPDATE PROCESS COMPLETED IN {total_time:.2f}s ===")
    
    # Save stats to file
    with open('update_stats.json', 'w') as f:
        json.dump(all_stats, f, indent=2)
    
    return all_stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update CMR data using Supabase")
    
    # General options
    parser.add_argument('--api-url', help="API URL for data crawling")
    
    # Step control arguments
    parser.add_argument('--skip-import', action='store_true', help="Skip data import")
    parser.add_argument('--skip-geocode', action='store_true', help="Skip geocoding")
    parser.add_argument('--skip-index', action='store_true', help="Skip search index rebuild")
    parser.add_argument('--skip-location-groups', action='store_true', help="Skip building location groups")
    parser.add_argument('--skip-views', action='store_true', help="Skip refreshing materialized views")
    
    # Limits
    parser.add_argument('--import-limit', type=int, help="Max components to import")
    parser.add_argument('--geocode-limit', type=int, default=500, help="Max components to geocode")
    
    args = parser.parse_args()
    
    # Run the update process
    update_with_supabase(args)