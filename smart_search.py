#!/usr/bin/env python3
"""
Smart search implementation that combines:
1. Redis cache for ultra-fast responses on common queries
2. PostgreSQL full-text search for complex queries
3. Intelligent query parsing for optimal search strategy
4. Result grouping for clean presentation
"""
import os
import re
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
import django
from django.core.cache import cache
from psycopg2.extras import RealDictCursor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

# Import Supabase connection
from supabase_integration import get_db_connection

def smart_search(query, page=1, per_page=20, sort_by='relevance', sort_order='desc', use_cache=True):
    """
    Smart search function that:
    1. Checks Redis cache first for common queries
    2. Uses the optimal search strategy based on query type
    3. Returns grouped results with pagination
    
    Args:
        query (str): Search query
        page (int): Page number
        per_page (int): Results per page
        sort_by (str): Field to sort by (relevance, location, date)
        sort_order (str): Sort order (asc, desc)
        use_cache (bool): Whether to use and update Redis cache
        
    Returns:
        dict: Search results and metadata
    """
    start_time = time.time()
    
    # Normalize query
    normalized_query = query.strip().lower()
    
    # Check Redis cache first if using cache
    if use_cache:
        cache_result = check_search_cache(normalized_query, page, per_page, sort_by, sort_order)
        if cache_result:
            # Add timing information
            cache_result['api_time'] = time.time() - start_time
            cache_result['from_cache'] = True
            return cache_result
    
    # Determine search strategy based on query
    search_strategy = determine_search_strategy(normalized_query)
    logger.info(f"Using search strategy: {search_strategy} for query: '{normalized_query}'")
    
    # Execute search with the appropriate strategy
    if search_strategy == 'cmu_id':
        results = search_by_cmu_id(normalized_query)
    elif search_strategy == 'location':
        results = search_by_location(normalized_query)
    elif search_strategy == 'company':
        results = search_by_company(normalized_query)
    elif search_strategy == 'technology':
        results = search_by_technology(normalized_query)
    else:  # 'full_text' or any other fallback
        results = search_full_text(normalized_query)
    
    # Group results by location
    grouped_results = group_results_by_location(results)
    
    # Apply sorting
    sorted_results = sort_grouped_results(grouped_results, sort_by, sort_order)
    
    # Apply pagination
    total_count = len(sorted_results)
    start_index = (page - 1) * per_page
    end_index = min(start_index + per_page, total_count)
    page_results = sorted_results[start_index:end_index]
    
    # Calculate pagination metadata
    total_pages = (total_count + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    # Prepare results
    search_results = {
        'query': query,
        'components': page_results,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev,
        'from_cache': False,
        'api_time': time.time() - start_time
    }
    
    # Cache results for future use if using cache
    if use_cache:
        cache_search_results(normalized_query, search_results)
    
    return search_results

def determine_search_strategy(query):
    """
    Determine the optimal search strategy based on the query.
    
    Args:
        query (str): Search query
        
    Returns:
        str: Search strategy ('cmu_id', 'location', 'company', 'technology', 'full_text')
    """
    # Check if query looks like a CMU ID (uppercase alphanumeric, possibly with hyphens)
    if re.match(r'^[A-Z0-9\-]{3,15}$', query):
        return 'cmu_id'
    
    # Check if query looks like a location search
    if re.search(r'\b(in|at|near)\b', query) or re.search(r'\b[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}\b', query):
        return 'location'
    
    # Check if query might be a company name (contains "Ltd", "Limited", etc.)
    if re.search(r'\b(ltd|limited|inc|incorporated|plc|llc|llp|gmbh|co|corporation)\b', query, re.IGNORECASE):
        return 'company'
    
    # Check if query might be a technology type
    tech_terms = ['solar', 'wind', 'hydro', 'battery', 'storage', 'gas', 'biomass', 'coal', 'nuclear', 'cogeneration']
    if any(term in query.lower() for term in tech_terms):
        return 'technology'
    
    # Default to full-text search
    return 'full_text'

def check_search_cache(query, page, per_page, sort_by, sort_order):
    """
    Check if search results exist in Redis cache.
    
    Args:
        query (str): Search query
        page (int): Page number
        per_page (int): Results per page
        sort_by (str): Field to sort by
        sort_order (str): Sort order
        
    Returns:
        dict or None: Cached search results if found, None otherwise
    """
    # Create a cache key that includes all parameters
    cache_key = f"search:{hashlib.md5(query.encode('utf-8')).hexdigest()}"
    
    # Try to get cached results
    cached_data = cache.get(cache_key)
    if not cached_data:
        return None
    
    try:
        data = json.loads(cached_data)
        
        # Check if the cached data includes the requested page
        if 'results' not in data:
            return None
        
        # We have all results in cache, now we need to apply sorting and pagination
        results = data['results']
        
        # Apply sorting
        if sort_by == 'relevance':
            results = sorted(results, key=lambda x: x.get('rank', 0), reverse=(sort_order == 'desc'))
        elif sort_by == 'location':
            results = sorted(results, key=lambda x: x.get('location', ''), reverse=(sort_order == 'desc'))
        elif sort_by == 'date':
            results = sorted(results, key=lambda x: x.get('delivery_year', ''), reverse=(sort_order == 'desc'))
        
        # Group results by location
        grouped_results = group_results_by_location(results)
        
        # Apply sorting to grouped results
        sorted_results = sort_grouped_results(grouped_results, sort_by, sort_order)
        
        # Apply pagination
        total_count = len(sorted_results)
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_count)
        page_results = sorted_results[start_index:end_index]
        
        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Prepare results
        search_results = {
            'query': query,
            'components': page_results,
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'cache_age': datetime.now() - datetime.fromisoformat(data['cached_at'])
        }
        
        logger.info(f"Cache hit for query '{query}' (page {page}/{total_pages})")
        return search_results
        
    except Exception as e:
        logger.error(f"Error parsing cached search results: {e}")
        return None

def cache_search_results(query, results):
    """
    Cache search results in Redis.
    
    Args:
        query (str): Search query
        results (dict): Search results
    """
    # Create a cache key
    cache_key = f"search:{hashlib.md5(query.encode('utf-8')).hexdigest()}"
    
    # Store raw results for flexible reuse
    cache_data = {
        'query': query,
        'results': results.get('components', []),
        'total_count': results.get('total_count', 0),
        'cached_at': datetime.now().isoformat(),
        'cache_version': 1
    }
    
    # Cache for 1 day
    cache.set(cache_key, json.dumps(cache_data), timeout=3600)  # 1 hour - reduce network egress
    logger.info(f"Cached search results for query '{query}' ({results.get('total_count', 0)} results)")

def search_by_cmu_id(query):
    """
    Search components by CMU ID.
    
    Args:
        query (str): CMU ID to search for
        
    Returns:
        list: List of components matching the CMU ID
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT id, cmu_id, company_name, location, technology, 
                   description, auction_name, delivery_year, derated_capacity_mw,
                   1.0 as rank  -- Fixed rank for direct matches
            FROM checker_component
            WHERE cmu_id ILIKE %s
            """, (f"%{query}%",))
            
            results = cursor.fetchall()
    
    return list(results)

def search_by_location(query):
    """
    Search components by location.
    
    Args:
        query (str): Location to search for
        
    Returns:
        list: List of components matching the location
    """
    # Extract location terms (after "in", "at", "near")
    location_terms = re.search(r'\b(in|at|near)\s+([A-Za-z\s,]+)', query)
    if location_terms:
        location = location_terms.group(2).strip()
    else:
        location = query
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT id, cmu_id, company_name, location, technology, 
                   description, auction_name, delivery_year, derated_capacity_mw,
                   similarity(location, %s) as rank
            FROM checker_component
            WHERE similarity(location, %s) > 0.2
            ORDER BY rank DESC
            LIMIT 200
            """, (location, location))
            
            results = cursor.fetchall()
    
    return list(results)

def search_by_company(query):
    """
    Search components by company name.
    
    Args:
        query (str): Company name to search for
        
    Returns:
        list: List of components matching the company name
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT id, cmu_id, company_name, location, technology, 
                   description, auction_name, delivery_year, derated_capacity_mw,
                   similarity(company_name, %s) as rank
            FROM checker_component
            WHERE similarity(company_name, %s) > 0.15
            ORDER BY rank DESC
            LIMIT 300
            """, (query, query))
            
            results = cursor.fetchall()
    
    return list(results)

def search_by_technology(query):
    """
    Search components by technology type.
    
    Args:
        query (str): Technology to search for
        
    Returns:
        list: List of components matching the technology
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT id, cmu_id, company_name, location, technology, 
                   description, auction_name, delivery_year, derated_capacity_mw,
                   similarity(technology, %s) as rank
            FROM checker_component
            WHERE similarity(technology, %s) > 0.15
            ORDER BY rank DESC
            LIMIT 500
            """, (query, query))
            
            results = cursor.fetchall()
    
    return list(results)

def search_full_text(query):
    """
    Search components using full-text search.
    
    Args:
        query (str): Search query
        
    Returns:
        list: List of components matching the search query
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT id, cmu_id, company_name, location, technology, 
                   description, auction_name, delivery_year, derated_capacity_mw,
                   ts_rank(search_vector, websearch_to_tsquery('english', %s)) as rank
            FROM checker_component
            WHERE search_vector @@ websearch_to_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT 1000
            """, (query, query))
            
            results = cursor.fetchall()
    
    return list(results)

def group_results_by_location(results):
    """
    Group search results by location and description.
    
    Args:
        results (list): List of component dictionaries
        
    Returns:
        list: List of grouped components
    """
    # Create groups
    groups = {}
    
    for comp in results:
        location = comp.get('location', '')
        description = comp.get('description', '')
        
        # Skip components without location
        if not location:
            continue
            
        # Create group key
        group_key = f"{location}:{description}"
        
        # Initialize group if it doesn't exist
        if group_key not in groups:
            groups[group_key] = {
                'location': location,
                'description': description,
                'cmu_ids': set(),
                'auction_names': set(),
                'components': [],
                'first_component': comp,
                'active_status': False,
                'count': 0,
                'max_rank': 0
            }
        
        # Update group info
        group = groups[group_key]
        group['components'].append(comp)
        group['count'] += 1
        
        # Track maximum rank for sorting by relevance
        rank = float(comp.get('rank', 0))
        group['max_rank'] = max(group['max_rank'], rank)
        
        # Add CMU ID if present
        cmu_id = comp.get('cmu_id', '')
        if cmu_id:
            group['cmu_ids'].add(cmu_id)
        
        # Add auction name if present
        auction_name = comp.get('auction_name', '')
        if auction_name:
            group['auction_names'].add(auction_name)
        
        # Check if this is an active component (2024 or later)
        delivery_year = comp.get('delivery_year', '')
        try:
            if delivery_year and int(delivery_year) >= 2024:
                group['active_status'] = True
        except (ValueError, TypeError):
            pass
    
    # Convert groups to a list
    grouped_results = []
    for group in groups.values():
        # Convert sets to lists
        group['cmu_ids'] = list(group['cmu_ids'])
        group['auction_names'] = list(group['auction_names'])
        grouped_results.append(group)
    
    return grouped_results

def sort_grouped_results(grouped_results, sort_by, sort_order):
    """
    Sort grouped results by the specified field.
    
    Args:
        grouped_results (list): List of grouped components
        sort_by (str): Field to sort by (relevance, location, date)
        sort_order (str): Sort order (asc, desc)
        
    Returns:
        list: Sorted list of grouped components
    """
    reverse = (sort_order == 'desc')
    
    if sort_by == 'relevance':
        return sorted(grouped_results, key=lambda x: x['max_rank'], reverse=reverse)
    elif sort_by == 'location':
        return sorted(grouped_results, key=lambda x: x['location'].lower(), reverse=reverse)
    elif sort_by == 'date':
        # Try to sort by the latest delivery year in the auction names
        def extract_year(group):
            delivery_years = []
            for comp in group['components']:
                year = comp.get('delivery_year', '')
                try:
                    if year:
                        delivery_years.append(int(year))
                except (ValueError, TypeError):
                    pass
            return max(delivery_years) if delivery_years else 0
        
        return sorted(grouped_results, key=extract_year, reverse=reverse)
    
    # Default to sorting by relevance
    return sorted(grouped_results, key=lambda x: x['max_rank'], reverse=True)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart search with Redis cache and PostgreSQL")
    parser.add_argument('query', help="Search query")
    parser.add_argument('--page', type=int, default=1, help="Page number")
    parser.add_argument('--per-page', type=int, default=20, help="Results per page")
    parser.add_argument('--sort-by', choices=['relevance', 'location', 'date'], default='relevance', help="Sort field")
    parser.add_argument('--sort-order', choices=['asc', 'desc'], default='desc', help="Sort order")
    parser.add_argument('--no-cache', action='store_true', help="Don't use cache")
    
    args = parser.parse_args()
    
    results = smart_search(
        args.query, 
        page=args.page, 
        per_page=args.per_page, 
        sort_by=args.sort_by, 
        sort_order=args.sort_order, 
        use_cache=not args.no_cache
    )
    
    print(f"Found {results['total_count']} results for '{args.query}' (page {results['page']}/{results['total_pages']})")
    print(f"API time: {results['api_time']:.3f}s, From cache: {results.get('from_cache', False)}")
    
    for i, group in enumerate(results['components']):
        print(f"\n{i+1}. {group['location']}")
        print(f"   Description: {group['description'][:50]}...")
        print(f"   Active: {'Yes' if group['active_status'] else 'No'}")
        print(f"   Components: {group['count']}")
        print(f"   CMU IDs: {', '.join(group['cmu_ids'][:3])}{' and more' if len(group['cmu_ids']) > 3 else ''}")
        print(f"   First Component: {group['first_component'].get('company_name', '')}, {group['first_component'].get('technology', '')}")