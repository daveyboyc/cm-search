"""
Cached filter options service following O3's battle-tested pattern.
Provides complete filter dropdowns without fetching all result IDs.
"""
import logging
from django.core.cache import cache
from django.db import connection
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# Cache TTL: 1 day (filters change infrequently)
CACHE_TTL = 86400

def get_all_technologies() -> List[str]:
    """
    Get all unique technologies from LocationGroup.
    Uses direct SQL query - no row fetching required.
    
    Returns:
        List of technology names sorted alphabetically
    """
    cache_key = "filter:technologies:v1"
    data = cache.get(cache_key)
    
    if data is None:
        logger.info("Cache MISS: Fetching all technologies from database")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT jsonb_object_keys(technologies::jsonb) AS tech
                FROM checker_locationgroup 
                WHERE technologies IS NOT NULL
                ORDER BY tech
            """)
            data = [row[0] for row in cursor.fetchall()]
        
        cache.set(cache_key, data, CACHE_TTL)
        logger.info(f"Cached {len(data)} technologies for {CACHE_TTL/3600:.1f} hours")
    else:
        logger.debug(f"Cache HIT: Retrieved {len(data)} technologies from cache")
    
    return data

def get_all_companies() -> List[str]:
    """
    Get all unique companies from LocationGroup.
    Uses direct SQL query - no row fetching required.
    
    Returns:
        List of company names sorted by number of locations (descending)
    """
    cache_key = "filter:companies:v2"
    data = cache.get(cache_key)
    
    if data is None:
        logger.info("Cache MISS: Fetching all companies from database")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT company, COUNT(*) as location_count
                FROM (
                    SELECT DISTINCT jsonb_object_keys(companies::jsonb) AS company
                    FROM checker_locationgroup 
                    WHERE companies IS NOT NULL
                ) AS company_locations
                GROUP BY company
                ORDER BY location_count DESC, company
            """)
            data = [row[0] for row in cursor.fetchall()]
        
        cache.set(cache_key, data, CACHE_TTL)
        logger.info(f"Cached {len(data)} companies for {CACHE_TTL/3600:.1f} hours")
    else:
        logger.debug(f"Cache HIT: Retrieved {len(data)} companies from cache")
    
    return data

def get_all_auction_years() -> List[str]:
    """
    Get all unique auction years from LocationGroup.
    Uses direct SQL query - no row fetching required.
    
    Returns:
        List of auction years sorted in descending order
    """
    cache_key = "filter:auction_years:v1"
    data = cache.get(cache_key)
    
    if data is None:
        logger.info("Cache MISS: Fetching all auction years from database")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT jsonb_array_elements_text(auction_years::jsonb) AS year
                FROM checker_locationgroup 
                WHERE auction_years IS NOT NULL
                ORDER BY year DESC
            """)
            data = [row[0] for row in cursor.fetchall()]
        
        cache.set(cache_key, data, CACHE_TTL)
        logger.info(f"Cached {len(data)} auction years for {CACHE_TTL/3600:.1f} hours")
    else:
        logger.debug(f"Cache HIT: Retrieved {len(data)} auction years from cache")
    
    return data

def get_complete_filter_options() -> Dict[str, List[str]]:
    """
    Get all filter options in a single call.
    More efficient than calling individual functions when you need all filters.
    
    Returns:
        Dictionary with keys: 'technologies', 'companies', 'auction_years'
    """
    cache_key = "filter:complete_options:v2"
    data = cache.get(cache_key)
    
    if data is None:
        logger.info("Cache MISS: Fetching complete filter options from database")
        
        # Use single connection for all queries
        with connection.cursor() as cursor:
            # Get technologies
            cursor.execute("""
                SELECT DISTINCT jsonb_object_keys(technologies::jsonb) AS tech
                FROM checker_locationgroup 
                WHERE technologies IS NOT NULL
                ORDER BY tech
            """)
            technologies = [row[0] for row in cursor.fetchall()]
            
            # Get companies ordered by number of locations they appear in
            cursor.execute("""
                SELECT company, COUNT(*) as location_count
                FROM (
                    SELECT DISTINCT jsonb_object_keys(companies::jsonb) AS company
                    FROM checker_locationgroup 
                    WHERE companies IS NOT NULL
                ) AS company_locations
                GROUP BY company
                ORDER BY location_count DESC, company
            """)
            companies = [row[0] for row in cursor.fetchall()]
            
            # Get auction years
            cursor.execute("""
                SELECT DISTINCT jsonb_array_elements_text(auction_years::jsonb) AS year
                FROM checker_locationgroup 
                WHERE auction_years IS NOT NULL
                ORDER BY year DESC
            """)
            auction_years = [row[0] for row in cursor.fetchall()]
        
        data = {
            'technologies': technologies,
            'companies': companies,
            'auction_years': auction_years
        }
        
        cache.set(cache_key, data, CACHE_TTL)
        logger.info(f"Cached complete filter options: {len(technologies)} techs, "
                   f"{len(companies)} companies, {len(auction_years)} years")
    else:
        logger.debug("Cache HIT: Retrieved complete filter options from cache")
    
    return data

def refresh_filter_caches() -> Dict[str, int]:
    """
    Force refresh of all filter caches.
    Useful for management commands or when data changes.
    
    Returns:
        Dictionary with cache refresh results
    """
    logger.info("Force refreshing all filter caches...")
    
    # Clear existing caches
    cache.delete_many([
        "filter:technologies:v1",
        "filter:companies:v1", 
        "filter:companies:v2",
        "filter:auction_years:v1",
        "filter:complete_options:v1",
        "filter:complete_options:v2"
    ])
    
    # Rebuild caches
    complete_options = get_complete_filter_options()
    
    # Also rebuild individual caches
    technologies = get_all_technologies()
    companies = get_all_companies()
    auction_years = get_all_auction_years()
    
    results = {
        'technologies': len(technologies),
        'companies': len(companies),
        'auction_years': len(auction_years)
    }
    
    logger.info(f"Filter caches refreshed: {results}")
    return results

def get_filter_stats() -> Dict[str, any]:
    """
    Get statistics about current filter cache state.
    Useful for monitoring and debugging.
    
    Returns:
        Dictionary with cache statistics
    """
    stats = {}
    
    cache_keys = [
        "filter:technologies:v1",
        "filter:companies:v1",
        "filter:auction_years:v1", 
        "filter:complete_options:v1"
    ]
    
    for key in cache_keys:
        data = cache.get(key)
        filter_type = key.split(':')[1]
        
        if data is None:
            stats[filter_type] = {'cached': False, 'count': 0}
        else:
            if isinstance(data, dict):
                # Complete options cache
                stats[filter_type] = {
                    'cached': True,
                    'technologies': len(data.get('technologies', [])),
                    'companies': len(data.get('companies', [])),
                    'auction_years': len(data.get('auction_years', []))
                }
            else:
                # Individual filter cache
                stats[filter_type] = {'cached': True, 'count': len(data)}
    
    return stats