"""
Pagination utilities for optimizing search result navigation in CMR

This module provides efficient pagination strategies:
1. Cursor-based pagination for consistent performance
2. Memory-efficient page navigation display
3. Smart result window caching
4. Pre-computed pagination metadata
"""

import time
import json
import logging
from datetime import datetime
from django.core.cache import cache

logger = logging.getLogger(__name__)

def generate_page_navigation(total_pages, current_page, window=2):
    """
    Generate a memory-efficient page navigation structure (e.g., 1, 2, ..., 8, 9, 10, ..., 99, 100)
    
    Args:
        total_pages (int): Total number of pages
        current_page (int): Current active page
        window (int): Number of pages to show around current page
        
    Returns:
        list: Page numbers to display, with '...' for skipped ranges
    """
    pages = []
    
    # Always include first page
    pages.append(1)
    
    # Add ellipsis if needed
    if current_page - window > 2:
        pages.append('...')
    
    # Pages around current page
    for i in range(max(2, current_page - window), min(current_page + window + 1, total_pages)):
        pages.append(i)
    
    # Add ellipsis if needed
    if current_page + window < total_pages - 1:
        pages.append('...')
    
    # Always include last page if not already included
    if total_pages > 1 and total_pages not in pages:
        pages.append(total_pages)
    
    return pages

def get_cursor_pagination(results, cursor=None, page_size=20):
    """
    Implement cursor-based pagination for consistent performance regardless of page
    
    Args:
        results (list): Complete result set
        cursor (str, optional): ID of the last item from previous page
        page_size (int): Number of items per page
        
    Returns:
        tuple: (paginated_results, next_cursor, prev_cursor)
    """
    if not results:
        return [], None, None
    
    # If cursor is None, start from beginning
    if cursor is None:
        paginated_results = results[:page_size]
        next_cursor = results[page_size-1]['id'] if len(results) >= page_size else None
        prev_cursor = None
    else:
        # Find index of cursor
        cursor_index = next((i for i, item in enumerate(results) if str(item.get('id', '')) == str(cursor)), None)
        if cursor_index is None:
            return [], None, None
        
        paginated_results = results[cursor_index+1:cursor_index+1+page_size]
        next_cursor = paginated_results[-1]['id'] if len(paginated_results) == page_size else None
        prev_cursor = cursor
        
    return paginated_results, next_cursor, prev_cursor

def smart_paginate(results, page=1, per_page=20):
    """
    Implement offset-based pagination with optimized metadata
    
    Args:
        results (list): Complete result set
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        
    Returns:
        dict: Pagination results and metadata
    """
    total_count = len(results)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    
    # Calculate slice indices
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_count)
    
    # Get page items
    page_items = results[start_idx:end_idx]
    
    # Generate page navigation
    page_navigation = generate_page_navigation(total_pages, page)
    
    # Prepare pagination metadata
    pagination = {
        "items": page_items,
        "total_count": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "page_navigation": page_navigation
    }
    
    return pagination

def cache_result_windows(results, query, per_page=20):
    """
    Cache strategic result windows for efficient navigation
    
    Args:
        results (list): Complete result set
        query (str): Search query
        per_page (int): Items per page
    """
    start_time = time.time()
    
    # Cache total result count and metadata
    total_count = len(results)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Cache first and last pages always
    first_page = results[:per_page]
    cache.set(f"search_page:{query}:1", first_page, timeout=3600)  # 1 hour - reduce network egress
    
    # Only cache last page if different from first
    if total_pages > 1:
        last_page_idx = (total_pages - 1) * per_page
        last_page = results[last_page_idx:last_page_idx + per_page]
        cache.set(f"search_page:{query}:{total_pages}", last_page, timeout=3600)  # 1 hour - reduce network egress
    
    # Cache pagination metadata
    page_navigation = generate_page_navigation(total_pages, 1)
    
    pagination_metadata = {
        "total_count": total_count,
        "total_pages": total_pages,
        "per_page": per_page,
        "page_navigation": page_navigation,
        "cached_at": datetime.now().isoformat()
    }
    
    cache.set(f"search_pagination:{query}", pagination_metadata, timeout=3600)  # 1 hour - reduce network egress
    
    logger.info(f"Cached result windows for query '{query}' in {time.time() - start_time:.3f}s")
    
    # For large result sets, strategically cache a few middle pages
    if total_pages > 10:
        # Cache around 25%, 50%, 75% marks for faster navigation
        for page_pct in [0.25, 0.5, 0.75]:
            middle_page = max(2, min(total_pages - 1, int(total_pages * page_pct)))
            middle_idx = (middle_page - 1) * per_page
            middle_items = results[middle_idx:middle_idx + per_page]
            cache.set(f"search_page:{query}:{middle_page}", middle_items, timeout=3600)  # 1 hour - reduce network egress
    
    # Return statistics
    return {
        "total_count": total_count, 
        "total_pages": total_pages,
        "windows_cached": 2 if total_pages <= 1 else min(5, total_pages)
    }

def get_cached_page(query, page, per_page=20, fallback_results=None):
    """
    Get a cached page or compute it from fallback results
    
    Args:
        query (str): Search query
        page (int): Page number
        per_page (int): Items per page
        fallback_results (list, optional): Complete results to use if cache misses
        
    Returns:
        tuple: (page_items, pagination_metadata, from_cache)
    """
    # Try to get from cache first
    cached_page = cache.get(f"search_page:{query}:{page}")
    cached_pagination = cache.get(f"search_pagination:{query}")
    
    if cached_page and cached_pagination:
        # Update navigation for current page
        cached_pagination["page"] = page
        cached_pagination["page_navigation"] = generate_page_navigation(
            cached_pagination["total_pages"], page
        )
        cached_pagination["has_next"] = page < cached_pagination["total_pages"]
        cached_pagination["has_prev"] = page > 1
        cached_pagination["items"] = cached_page
        
        return cached_pagination, True
    
    # If no cache or missing piece, compute from fallback
    if fallback_results:
        pagination = smart_paginate(fallback_results, page, per_page)
        return pagination, False
    
    # No cache and no fallback
    return None, False