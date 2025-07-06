#!/usr/bin/env python
"""
Enhanced Smart Search Implementation for CMR

This improved version includes:
- Optimized pagination with page navigation
- Cursor-based pagination option for consistent performance
- Result window caching for efficient "Jump to page" functionality
- Detailed performance metrics collection

Usage:
  python enhanced_smart_search.py [query] [options]
"""

import os
import sys
import re
import json
import time
import argparse
import logging
import hashlib
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from django.core.cache import cache

# Import pagination utilities
from pagination_utils import (
    smart_paginate,
    get_cursor_pagination,
    cache_result_windows,
    get_cached_page
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("enhanced_search.log")
    ]
)
logger = logging.getLogger(__name__)

# Import the PostgreSQL connection details
try:
    from supabase_integration import get_db_connection, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    logger.info("Successfully imported connection details from supabase_integration.py")
except ImportError:
    # Fallback to environment variables or local configuration
    DB_HOST = os.environ.get("DB_HOST", "aws-0-eu-west-2.pooler.supabase.com")
    DB_PORT = os.environ.get("DB_PORT", "6543")
    DB_NAME = os.environ.get("DB_NAME", "postgres")
    DB_USER = os.environ.get("DB_USER", "postgres.vixsiceyuolxzmqijpds")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "vzIU91Rn55qgV95y")
    
    def get_db_connection():
        """Get a PostgreSQL database connection."""
        try:
            return psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                options="-c search_path=public"
            )
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    logger.warning("Could not import from supabase_integration.py, using fallback configuration")

# Define Redis connection
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Enhanced smart search for CMR components')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--page', type=int, default=1, help='Page number')
    parser.add_argument('--per-page', type=int, default=20, help='Results per page')
    parser.add_argument('--cursor', help='Cursor for cursor-based pagination')
    parser.add_argument('--sort-by', choices=['relevance', 'delivery_year', 'location'], 
                       default='relevance', help='Sort field')
    parser.add_argument('--sort-order', choices=['asc', 'desc'], 
                       default='desc', help='Sort order')
    parser.add_argument('--no-cache', action='store_true', help='Skip cache lookup')
    parser.add_argument('--use-cursor', action='store_true', help='Use cursor-based pagination')
    parser.add_argument('--collect-metrics', action='store_true', help='Collect detailed performance metrics')
    return parser.parse_args()

def determine_search_strategy(query):
    """
    Analyze query to determine the optimal search strategy
    Returns strategy type and any additional parameters
    """
    if not query:
        return 'empty', {}
    
    query = query.strip()
    
    # CMU ID pattern (e.g., "CMRS-T-1234")
    if re.match(r'^(CM|T)[A-Z0-9\-]{2,15}$', query, re.IGNORECASE):
        return 'cmu_id', {'exact': True}
    
    # Postcode pattern (e.g., "SW1A 1AA" or "SW1A")
    if re.match(r'^[A-Z]{1,2}[0-9][A-Z0-9]?(\s*[0-9][A-Z]{2})?$', query, re.IGNORECASE):
        return 'location', {'type': 'postcode'}
    
    # County/City pattern (mostly alphabetic)
    if re.match(r'^[A-Z\s\-]+$', query, re.IGNORECASE) and len(query) > 3:
        return 'location', {'type': 'area'}
    
    # Technology pattern (known technologies)
    tech_patterns = ['battery', 'nuclear', 'solar', 'wind', 'gas', 'coal', 'dsr', 'chp', 'hydro']
    if query.lower() in tech_patterns:
        return 'technology', {}
    
    # Company search pattern (check for well-known companies)
    company_patterns = ['edf', 'sse', 'drax', 'vital', 'flexitricity', 'engie', 'sge', 'tata']
    if any(company.lower() == query.lower() for company in company_patterns):
        return 'company', {'exact': True}
    
    # Multi-word query
    if ' ' in query:
        words = query.split()
        
        # Check if it looks like a location query (e.g., "London City")
        location_words = ['north', 'south', 'east', 'west', 'city', 'park', 'london', 'manchester', 
                         'birmingham', 'leeds', 'edinburgh', 'glasgow', 'belfast', 'bristol']
        location_matches = sum(1 for word in words if word.lower() in location_words)
        if location_matches / len(words) > 0.3:  # If 30% of words match location patterns
            return 'location', {'type': 'multi_word'}
        
        # Check if it looks like a company query
        company_words = ['energy', 'power', 'generation', 'limited', 'ltd', 'plc', 'llc', 'llp', 'gmbh', 'co', 'corporation']
        company_matches = sum(1 for word in words if word.lower() in company_words)
        if company_matches / len(words) > 0.3:  # If 30% of words match company patterns
            return 'company', {'type': 'multi_word'}
    
    # Default to general search
    return 'general', {}

def normalize_location(loc):
    """Normalize location for consistent grouping."""
    if not loc:
        return ""
        
    # Convert to lowercase and strip whitespace
    norm = str(loc).lower().strip()
    
    # Simple replacements
    norm = norm.replace(',', ' ')
    norm = norm.replace('.', ' ')
    norm = norm.replace('-', ' ')
    norm = norm.replace('_', ' ')
    norm = norm.replace('/', ' ')
    norm = norm.replace('\\', ' ')
    
    # Replace multiple spaces with single space
    while '  ' in norm:
        norm = norm.replace('  ', ' ')
        
    return norm

def group_results_by_location(results):
    """
    Group search results by normalized location and description
    Returns grouped results with first component and count for each group
    """
    location_groups = {}
    
    for result in results:
        # Create normalized location key
        norm_location = normalize_location(result.get('location', ''))
        description = result.get('description', '')
        group_key = (norm_location, description)
        
        # Initialize group if not seen before
        if group_key not in location_groups:
            location_groups[group_key] = {
                'location': result.get('location', ''),
                'description': description,
                'cmu_ids': set(),
                'auction_names': set(),
                'active_status': False,
                'components': [],
                'first_component': result,
                'count': 0,
                'max_rank': 0
            }
        
        # Add component to group
        group = location_groups[group_key]
        group['components'].append(result)
        group['count'] += 1
        
        # Track maximum rank for sorting by relevance
        rank = float(result.get('rank', 0))
        group['max_rank'] = max(group['max_rank'], rank)
        
        # Add CMU ID if present
        if result.get('cmu_id'):
            group['cmu_ids'].add(result.get('cmu_id'))
        
        # Add auction name if present
        if result.get('auction_name'):
            group['auction_names'].add(result.get('auction_name'))
        
        # Check if this auction makes the group active (2024 or later)
        delivery_year = result.get('delivery_year', '')
        try:
            if delivery_year and int(delivery_year) >= 2024:
                group['active_status'] = True
        except (ValueError, TypeError):
            pass
    
    # Convert location_groups to a serializable format
    serializable_groups = []
    for group_key, group in location_groups.items():
        # Convert sets to sorted lists
        group['cmu_ids'] = sorted(list(group['cmu_ids']))
        group['auction_names'] = sorted(list(group['auction_names']))
        
        # Add unique ID for the group (for cursor-based pagination)
        group['id'] = f"group_{len(serializable_groups)}"
        
        # Add group to result list
        serializable_groups.append(group)
    
    return serializable_groups

def enhanced_smart_search(query, page=1, per_page=20, cursor=None, sort_by='relevance', 
                         sort_order='desc', use_cache=True, use_cursor_pagination=False,
                         collect_metrics=False):
    """
    Enhanced smart search with improved pagination and metrics collection
    
    Args:
        query: Search term
        page: Page number (1-indexed)
        per_page: Results per page
        cursor: Cursor for cursor-based pagination
        sort_by: Field to sort by ('relevance', 'delivery_year', 'location')
        sort_order: Sort order ('asc' or 'desc')
        use_cache: Whether to check and use Redis cache
        use_cursor_pagination: Whether to use cursor-based pagination
        collect_metrics: Whether to collect detailed performance metrics
        
    Returns:
        dict: Search results with pagination metadata and metrics
    """
    metrics = {
        "timings": {},
        "cache_hits": {},
        "database_queries": 0
    }
    
    overall_start_time = time.time()
    
    if not query:
        return {
            "error": "No search query provided",
            "total_count": 0, 
            "processing_time": 0,
            "metrics": metrics if collect_metrics else None
        }
    
    # Normalize query
    query = query.strip()
    
    # Create cache key
    cache_key = f"enhanced_search_{hashlib.md5(query.lower().encode()).hexdigest()}_{sort_by}_{sort_order}"
    pagination_cache_key = f"search_pagination:{query}"
    
    cache_start_time = time.time()
    
    # Try to get from cache if enabled
    if use_cache:
        # Check if we can use cached pagination
        if not use_cursor_pagination:
            # Try to get the requested page from cache
            cached_pagination, from_cache = get_cached_page(query, page, per_page)
            
            if cached_pagination:
                if collect_metrics:
                    metrics["timings"]["cache_lookup"] = time.time() - cache_start_time
                    metrics["cache_hits"]["pagination"] = from_cache
                    metrics["timings"]["total"] = time.time() - overall_start_time
                
                logger.info(f"Cache hit for query '{query}' (page {page})")
                
                return {
                    "query": query,
                    "components": cached_pagination["items"],
                    "page_navigation": cached_pagination["page_navigation"],
                    "total_count": cached_pagination["total_count"],
                    "page": cached_pagination["page"],
                    "per_page": cached_pagination["per_page"],
                    "total_pages": cached_pagination["total_pages"],
                    "has_next": cached_pagination["has_next"],
                    "has_prev": cached_pagination["has_prev"],
                    "from_cache": True,
                    "processing_time": time.time() - overall_start_time,
                    "metrics": metrics if collect_metrics else None
                }
        
        # For cursor pagination or if page cache missed, check for full results cache
        cached_data = cache.get(cache_key)
        if cached_data:
            if collect_metrics:
                metrics["timings"]["cache_lookup"] = time.time() - cache_start_time
                metrics["cache_hits"]["full_results"] = True
            
            # Extract from cache
            data = json.loads(cached_data)
            results = data.get('results', [])
            
            # Apply sorting if needed
            sort_start_time = time.time()
            if sort_by == 'relevance':
                results = sorted(results, key=lambda x: x.get('rank', 0), reverse=(sort_order == 'desc'))
            elif sort_by == 'location':
                results = sorted(results, key=lambda x: x.get('location', '').lower(), reverse=(sort_order == 'desc'))
            elif sort_by == 'delivery_year':
                results = sorted(results, key=lambda x: x.get('delivery_year', ''), reverse=(sort_order == 'desc'))
            
            if collect_metrics:
                metrics["timings"]["sorting"] = time.time() - sort_start_time
            
            # Group results
            group_start_time = time.time()
            grouped_results = group_results_by_location(results)
            if collect_metrics:
                metrics["timings"]["grouping"] = time.time() - group_start_time
            
            # Apply pagination
            pagination_start_time = time.time()
            if use_cursor_pagination:
                paginated_items, next_cursor, prev_cursor = get_cursor_pagination(
                    grouped_results, cursor, per_page
                )
                
                # Cache result windows for efficient navigation
                if not cursor:  # Only cache on first page
                    cache_result_windows(grouped_results, query, per_page)
                
                if collect_metrics:
                    metrics["timings"]["pagination"] = time.time() - pagination_start_time
                    metrics["timings"]["total"] = time.time() - overall_start_time
                
                return {
                    "query": query,
                    "components": paginated_items,
                    "next_cursor": next_cursor,
                    "prev_cursor": prev_cursor,
                    "total_count": len(grouped_results),
                    "per_page": per_page,
                    "from_cache": True,
                    "processing_time": time.time() - overall_start_time,
                    "metrics": metrics if collect_metrics else None
                }
            else:
                # Use offset-based pagination
                pagination = smart_paginate(grouped_results, page, per_page)
                
                # Cache result windows for efficient navigation
                if page == 1:  # Only cache on first page
                    cache_result_windows(grouped_results, query, per_page)
                
                if collect_metrics:
                    metrics["timings"]["pagination"] = time.time() - pagination_start_time
                    metrics["timings"]["total"] = time.time() - overall_start_time
                
                return {
                    "query": query,
                    "components": pagination["items"],
                    "page_navigation": pagination["page_navigation"],
                    "total_count": pagination["total_count"], 
                    "page": pagination["page"],
                    "per_page": pagination["per_page"],
                    "total_pages": pagination["total_pages"],
                    "has_next": pagination["has_next"],
                    "has_prev": pagination["has_prev"],
                    "from_cache": True,
                    "processing_time": time.time() - overall_start_time,
                    "metrics": metrics if collect_metrics else None
                }
    
    if collect_metrics:
        metrics["timings"]["cache_lookup"] = time.time() - cache_start_time
        metrics["cache_hits"]["full_results"] = False
    
    # If not in cache, determine search strategy
    strategy_start_time = time.time()
    strategy, strategy_params = determine_search_strategy(query)
    if collect_metrics:
        metrics["timings"]["strategy_determination"] = time.time() - strategy_start_time
    
    logger.info(f"Using search strategy: {strategy} with params: {strategy_params}")
    
    # Build query based on strategy
    db_start_time = time.time()
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if collect_metrics:
                    metrics["database_queries"] += 1
                
                sql_query = ""
                sql_params = []
                
                # CMU ID search
                if strategy == 'cmu_id':
                    if strategy_params.get('exact', False):
                        sql_query = """
                            SELECT id, cmu_id, company_name, location, technology, 
                                   description, auction_name, delivery_year, status, type,
                                   component_id, derated_capacity_mw,
                                   1.0 as rank  -- Fixed rank for direct matches
                            FROM checker_component
                            WHERE cmu_id ILIKE %s
                            ORDER BY delivery_year DESC
                        """
                        sql_params = [query]
                    else:
                        sql_query = """
                            SELECT id, cmu_id, company_name, location, technology, 
                                   description, auction_name, delivery_year, status, type,
                                   component_id, derated_capacity_mw,
                                   ts_rank(search_vector, to_tsquery('english', %s)) AS rank
                            FROM checker_component
                            WHERE search_vector @@ to_tsquery('english', %s)
                            AND cmu_id ILIKE %s
                            ORDER BY rank DESC, delivery_year DESC
                        """
                        sql_params = [query, query, f"%{query}%"]
                
                # Location search
                elif strategy == 'location':
                    location_type = strategy_params.get('type', '')
                    
                    if location_type == 'postcode':
                        # Exact postcode match first, then outward code
                        if ' ' in query:
                            # Full postcode with space
                            outward = query.split()[0].upper()
                            sql_query = """
                                SELECT id, cmu_id, company_name, location, technology, 
                                       description, auction_name, delivery_year, status, type,
                                       component_id, derated_capacity_mw,
                                       CASE 
                                           WHEN location ILIKE %s THEN 1.0
                                           WHEN outward_code = %s THEN 0.8
                                           ELSE 0.5
                                       END as rank
                                FROM checker_component
                                WHERE location ILIKE %s OR outward_code = %s
                                ORDER BY 
                                    rank DESC,
                                    delivery_year DESC
                            """
                            sql_params = [f"%{query}%", outward, f"%{query}%", outward]
                        else:
                            # Just outward code
                            sql_query = """
                                SELECT id, cmu_id, company_name, location, technology, 
                                       description, auction_name, delivery_year, status, type,
                                       component_id, derated_capacity_mw,
                                       CASE 
                                           WHEN outward_code = %s THEN 1.0
                                           WHEN location ILIKE %s THEN 0.8
                                           ELSE 0.5
                                       END as rank
                                FROM checker_component
                                WHERE outward_code = %s OR location ILIKE %s
                                ORDER BY 
                                    rank DESC,
                                    delivery_year DESC
                            """
                            sql_params = [query.upper(), f"%{query}%", query.upper(), f"%{query}%"]
                    
                    elif location_type == 'area':
                        # County or city search
                        sql_query = """
                            SELECT id, cmu_id, company_name, location, technology, 
                                   description, auction_name, delivery_year, status, type,
                                   component_id, derated_capacity_mw,
                                   CASE 
                                       WHEN county ILIKE %s THEN 1.0
                                       WHEN location ILIKE %s THEN 0.8
                                       ELSE 0.5
                                   END as rank
                            FROM checker_component
                            WHERE county ILIKE %s OR location ILIKE %s
                            ORDER BY 
                                rank DESC,
                                delivery_year DESC
                        """
                        sql_params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
                    
                    else:  # Multi-word or other
                        # General location search with full-text capabilities
                        # Preprocess query for to_tsquery
                        ts_query = ' & '.join(query.split())
                        sql_query = """
                            SELECT id, cmu_id, company_name, location, technology, 
                                   description, auction_name, delivery_year, status, type,
                                   component_id, derated_capacity_mw,
                                   ts_rank(search_vector, to_tsquery('english', %s)) AS rank
                            FROM checker_component
                            WHERE search_vector @@ to_tsquery('english', %s)
                            AND (location IS NOT NULL AND location != '')
                            ORDER BY rank DESC, delivery_year DESC
                        """
                        sql_params = [ts_query, ts_query]
                
                # Technology search
                elif strategy == 'technology':
                    sql_query = """
                        SELECT id, cmu_id, company_name, location, technology, 
                               description, auction_name, delivery_year, status, type,
                               component_id, derated_capacity_mw,
                               CASE 
                                   WHEN technology ILIKE %s THEN 1.0
                                   ELSE 0.5
                               END as rank
                        FROM checker_component
                        WHERE technology ILIKE %s
                    """
                    
                    # Apply sorting based on sort_by parameter
                    if sort_by == 'delivery_year':
                        sql_query += f" ORDER BY delivery_year {'DESC' if sort_order == 'desc' else 'ASC'}"
                    elif sort_by == 'location':
                        sql_query += f" ORDER BY location {'DESC' if sort_order == 'desc' else 'ASC'}, delivery_year DESC"
                    else:  # Default to sorting by rank and delivery_year
                        sql_query += " ORDER BY rank DESC, delivery_year DESC"
                    
                    sql_params = [f"%{query}%", f"%{query}%"]
                
                # Company search
                elif strategy == 'company':
                    if strategy_params.get('exact', False):
                        sql_query = """
                            SELECT id, cmu_id, company_name, location, technology, 
                                   description, auction_name, delivery_year, status, type,
                                   component_id, derated_capacity_mw,
                                   1.0 as rank  -- Fixed rank for direct matches
                            FROM checker_component
                            WHERE company_name ILIKE %s
                        """
                        sql_params = [f"%{query}%"]
                    else:
                        sql_query = """
                            SELECT id, cmu_id, company_name, location, technology, 
                                   description, auction_name, delivery_year, status, type,
                                   component_id, derated_capacity_mw,
                                   ts_rank(search_vector, to_tsquery('english', %s)) AS rank
                            FROM checker_component
                            WHERE search_vector @@ to_tsquery('english', %s)
                            AND company_name ILIKE %s
                        """
                        sql_params = [query, query, f"%{query}%"]
                    
                    # Apply sorting based on sort_by parameter
                    if sort_by == 'delivery_year':
                        sql_query += f" ORDER BY delivery_year {'DESC' if sort_order == 'desc' else 'ASC'}"
                    elif sort_by == 'location':
                        sql_query += f" ORDER BY location {'DESC' if sort_order == 'desc' else 'ASC'}, delivery_year DESC"
                    elif 'rank' in sql_query:  # If using full-text search
                        sql_query += " ORDER BY rank DESC, delivery_year DESC"
                    else:  # Default to sorting by delivery_year
                        sql_query += " ORDER BY delivery_year DESC"
                
                # General search (fallback)
                else:
                    # Preprocess query for to_tsquery
                    ts_query = ' & '.join(query.split())
                    sql_query = """
                        SELECT id, cmu_id, company_name, location, technology, 
                               description, auction_name, delivery_year, status, type,
                               component_id, derated_capacity_mw,
                               ts_rank(search_vector, to_tsquery('english', %s)) AS rank
                        FROM checker_component
                        WHERE search_vector @@ to_tsquery('english', %s)
                        ORDER BY rank DESC, delivery_year DESC
                    """
                    sql_params = [ts_query, ts_query]
                
                # Add LIMIT to prevent memory issues
                # But get enough results for pagination
                full_sql_query = sql_query + " LIMIT 1000"  # Limit to 1000 for reasonable memory usage
                
                # Execute query and fetch results
                cursor.execute(full_sql_query, sql_params)
                all_results = cursor.fetchall()
                
                # Get total count (for accurate pagination)
                if collect_metrics:
                    count_start_time = time.time()
                    metrics["database_queries"] += 1
                
                count_sql = f"SELECT COUNT(*) FROM ({sql_query.split('ORDER BY')[0]}) as count_query"
                cursor.execute(count_sql, sql_params)
                total_count = cursor.fetchone()['count']
                
                if collect_metrics:
                    metrics["timings"]["count_query"] = time.time() - count_start_time
    
    except Exception as e:
        logger.error(f"Error executing search: {e}")
        return {
            "error": str(e),
            "total_count": 0,
            "processing_time": time.time() - overall_start_time,
            "metrics": metrics if collect_metrics else None
        }
    
    if collect_metrics:
        metrics["timings"]["database_query"] = time.time() - db_start_time
    
    # Group results
    group_start_time = time.time()
    grouped_results = group_results_by_location(all_results)
    if collect_metrics:
        metrics["timings"]["grouping"] = time.time() - group_start_time
    
    # Apply pagination
    pagination_start_time = time.time()
    if use_cursor_pagination:
        paginated_results, next_cursor, prev_cursor = get_cursor_pagination(
            grouped_results, cursor, per_page
        )
        
        # Cache the full results if using cache
        if use_cache:
            cache_data = json.dumps({
                'results': all_results,
                'cached_at': datetime.now().isoformat(),
                'total_count': total_count,
                'query': query,
                'strategy': strategy
            })
            cache.set(cache_key, cache_data, timeout=3600)  # Cache for 1 hour - reduce network egress
            
            # Also cache result windows for efficient navigation
            cache_result_windows(grouped_results, query, per_page)
        
        if collect_metrics:
            metrics["timings"]["pagination"] = time.time() - pagination_start_time
            metrics["timings"]["total"] = time.time() - overall_start_time
        
        return {
            "query": query,
            "components": paginated_results,
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
            "total_count": len(grouped_results),
            "per_page": per_page,
            "from_cache": False,
            "processing_time": time.time() - overall_start_time,
            "strategy": strategy,
            "metrics": metrics if collect_metrics else None
        }
    else:
        # Use offset-based pagination
        pagination = smart_paginate(grouped_results, page, per_page)
        
        # Cache the full results if using cache
        if use_cache:
            cache_data = json.dumps({
                'results': all_results,
                'cached_at': datetime.now().isoformat(),
                'total_count': total_count,
                'query': query,
                'strategy': strategy
            })
            cache.set(cache_key, cache_data, timeout=3600)  # Cache for 1 hour - reduce network egress
            
            # Also cache result windows for efficient navigation
            cache_result_windows(grouped_results, query, per_page)
        
        if collect_metrics:
            metrics["timings"]["pagination"] = time.time() - pagination_start_time
            metrics["timings"]["total"] = time.time() - overall_start_time
        
        return {
            "query": query,
            "components": pagination["items"],
            "page_navigation": pagination["page_navigation"],
            "total_count": pagination["total_count"],
            "page": pagination["page"],
            "per_page": pagination["per_page"],
            "total_pages": pagination["total_pages"],
            "has_next": pagination["has_next"],
            "has_prev": pagination["has_prev"],
            "from_cache": False,
            "processing_time": time.time() - overall_start_time,
            "strategy": strategy,
            "metrics": metrics if collect_metrics else None
        }

def main():
    """Main function to run the enhanced smart search"""
    args = parse_args()
    
    if not args.query:
        print("Please provide a search query.")
        return
    
    results = enhanced_smart_search(
        args.query, 
        page=args.page, 
        per_page=args.per_page,
        cursor=args.cursor,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
        use_cache=not args.no_cache,
        use_cursor_pagination=args.use_cursor,
        collect_metrics=args.collect_metrics
    )
    
    # Print search stats
    print(f"\nSearch query: '{args.query}'")
    print(f"Processing time: {results.get('processing_time', 0):.3f} seconds")
    print(f"From cache: {results.get('from_cache', False)}")
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    # Print pagination info
    if args.use_cursor:
        print(f"Showing {len(results.get('components', []))} of {results.get('total_count', 0)} results")
        print(f"Next cursor: {results.get('next_cursor')}")
        print(f"Previous cursor: {results.get('prev_cursor')}")
    else:
        print(f"Page {results.get('page', 1)} of {results.get('total_pages', 1)}")
        print(f"Showing {len(results.get('components', []))} of {results.get('total_count', 0)} results")
        print(f"Page navigation: {results.get('page_navigation', [])}")
    
    # Print metrics if collected
    if args.collect_metrics and 'metrics' in results:
        print("\nPerformance Metrics:")
        metrics = results['metrics']
        
        print("Timings:")
        for timing_key, timing_value in metrics.get('timings', {}).items():
            print(f"  {timing_key}: {timing_value:.3f}s")
        
        print("Cache hits:")
        for cache_key, cache_hit in metrics.get('cache_hits', {}).items():
            print(f"  {cache_key}: {'Yes' if cache_hit else 'No'}")
        
        print(f"Database queries: {metrics.get('database_queries', 0)}")
    
    # Print results
    print(f"\nShowing {len(results.get('components', []))} grouped locations:")
    for i, group in enumerate(results.get('components', [])):
        print(f"\n{i+1}. {group.get('location', 'Unknown location')}")
        print(f"   Description: {group.get('description', 'No description')[:50]}...")
        print(f"   Active: {'Yes' if group.get('active_status', False) else 'No'}")
        print(f"   Components: {group.get('count', 0)}")
        print(f"   CMU IDs: {', '.join(group.get('cmu_ids', [])[:3])}{' and more' if len(group.get('cmu_ids', [])) > 3 else ''}")
        if 'first_component' in group:
            first = group['first_component']
            print(f"   First Component: {first.get('company_name', '')}, {first.get('technology', '')}")
    
if __name__ == "__main__":
    main()