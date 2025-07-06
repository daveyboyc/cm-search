#!/usr/bin/env python3
"""
Script to optimize search and update caches without requiring Supabase.
This script uses direct PostgreSQL features through Django's connection.
"""
import os
import sys
import time
import logging
import django
from django.db import connection
from django.core.cache import cache

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

def rebuild_search_index():
    """
    Rebuild the full-text search index for all components.
    """
    start_time = time.time()
    logger.info("Rebuilding full-text search index...")
    
    try:
        with connection.cursor() as cursor:
            # Update search vectors for all components
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
            """)
            
            count = cursor.rowcount
            logger.info(f"Updated search vectors for {count} components")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Search index rebuild completed in {elapsed_time:.2f}s")
        return True
    
    except Exception as e:
        logger.error(f"Error rebuilding search index: {e}")
        return False

def build_location_groups_cache():
    """
    Build and cache location groups.
    Groups components by location and description.
    """
    from checker.models import Component
    from checker.templatetags.checker_tags import group_by_location
    import hashlib
    import json
    
    start_time = time.time()
    logger.info("Building location groups cache...")
    
    try:
        # Get all components
        components = Component.objects.values(
            'id', 'location', 'description', 'cmu_id', 'auction_name', 
            'company_name', 'technology', 'delivery_year', 'derated_capacity_mw'
        )
        
        logger.info(f"Retrieved {len(components)} components")
        
        # Group components by location
        grouped_components = group_by_location(components)
        
        logger.info(f"Created {len(grouped_components)} location groups")
        
        # Cache each group individually
        cached_count = 0
        
        for group in grouped_components:
            location = group['location']
            description = group['description']
            
            # Create a cache key
            key_seed = f"{location}_{description}"
            cache_key = f"loc_group:{hashlib.md5(key_seed.encode('utf-8')).hexdigest()}"
            
            # Cache the group
            cache.set(cache_key, json.dumps(group), None)  # None = never expire
            cached_count += 1
        
        # Cache the list of groups
        cache.set("all_location_groups", [g['location'] for g in grouped_components], None)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Location groups cache build completed in {elapsed_time:.2f}s")
        logger.info(f"Cached {cached_count} location groups")
        
        return True
    
    except Exception as e:
        logger.error(f"Error building location groups cache: {e}")
        return False

def build_map_cache():
    """
    Build cache for map data.
    """
    from checker.models import Component
    import json
    
    start_time = time.time()
    logger.info("Building map data cache...")
    
    try:
        # Get all geocoded components
        geocoded_components = Component.objects.filter(
            geocoded=True,
            latitude__isnull=False,
            longitude__isnull=False
        ).values(
            'id', 'location', 'technology', 'company_name',
            'latitude', 'longitude', 'derated_capacity_mw',
            'delivery_year'
        )
        
        logger.info(f"Retrieved {geocoded_components.count()} geocoded components")
        
        # Group by technology
        technologies = Component.objects.values_list('technology', flat=True).distinct()
        
        for tech in technologies:
            if not tech:
                continue
                
            # Filter components for this technology
            tech_components = [c for c in geocoded_components if c['technology'] == tech]
            
            # Skip if no components
            if not tech_components:
                continue
                
            # Create a cache key
            cache_key = f"map_data:tech:{tech}"
            
            # Cache the data
            cache.set(cache_key, json.dumps(tech_components), None)  # None = never expire
            
            logger.info(f"Cached {len(tech_components)} components for technology '{tech}'")
        
        # Cache all components
        cache.set("map_data:all", json.dumps(list(geocoded_components)), None)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Map data cache build completed in {elapsed_time:.2f}s")
        
        return True
    
    except Exception as e:
        logger.error(f"Error building map data cache: {e}")
        return False

def run_optimizations():
    """Run all optimization steps"""
    results = {}
    
    # Step 1: Rebuild search index
    search_result = rebuild_search_index()
    results["search_index"] = "Success" if search_result else "Failed"
    
    # Step 2: Build location groups cache
    groups_result = build_location_groups_cache()
    results["location_groups"] = "Success" if groups_result else "Failed"
    
    # Step 3: Build map cache
    map_result = build_map_cache()
    results["map_cache"] = "Success" if map_result else "Failed"
    
    # Print summary
    logger.info("===== Optimization Results =====")
    for step, status in results.items():
        logger.info(f"{step}: {status}")
    
    return all(status == "Success" for status in results.values())

if __name__ == "__main__":
    success = run_optimizations()
    sys.exit(0 if success else 1)