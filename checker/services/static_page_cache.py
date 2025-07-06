"""
Static Page Cache Service for All Locations Performance Optimization

This service implements aggressive caching for the "All locations" page which always
starts A-Z sorted. Since 90% of users access the first 2 pages, we pre-cache these
as static responses to eliminate database queries and reduce egress by 75%.

Key Features:
- Pre-cache first 4 pages of A-Z sorted results
- Cache versioning with LocationGroup checksum
- Background cache warming
- Graceful fallback on cache miss
- Smart invalidation when data changes
"""

import json
import time
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_VERSION = "v1.0"
STATIC_PAGE_KEY_PREFIX = f"static_page_{CACHE_VERSION}:"
STATIC_PAGE_EXPIRATION = 60 * 60 * 24  # 24 hours (data changes daily at most)
CACHE_CHECKSUM_KEY = f"locationgroup_checksum_{CACHE_VERSION}"
CACHE_METADATA_KEY = f"cache_metadata_{CACHE_VERSION}"

# Pages to pre-cache (first 4 pages handle 95% of traffic)
PAGES_TO_CACHE = [1, 2, 3, 4]
ITEMS_PER_PAGE = 25


class StaticPageCacheService:
    """
    Service for managing static page caching for the All Locations view.
    
    This service pre-caches the most commonly accessed pages and provides
    fast retrieval with automatic cache warming and invalidation.
    """
    
    def __init__(self):
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0
        }
    
    def get_cache_key(self, page: int, per_page: int = 25, 
                     status_filter: str = 'all', 
                     auction_filter: str = '',
                     technology_filter: str = '',
                     company_filter: str = '',
                     sort_by: str = 'location',
                     sort_order: str = 'asc') -> str:
        """
        Generate cache key for a specific page configuration.
        
        Args:
            page: Page number
            per_page: Items per page
            status_filter: Active/inactive filter
            auction_filter: Auction year filter
            technology_filter: Technology filter
            company_filter: Company filter
            sort_by: Sort field (location, components, etc.)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Cache key string
        """
        # Create deterministic key based on all parameters
        key_parts = [
            'all_locations',
            f'page_{page}',
            f'per_page_{per_page}',
            f'status_{status_filter}',
            f'auction_{auction_filter}',
            f'tech_{technology_filter}',
            f'company_{company_filter}',
            f'sort_{sort_by}_{sort_order}'
        ]
        
        # Remove empty filters to normalize keys
        normalized_key = '_'.join([part for part in key_parts if not part.endswith('_')])
        
        return f"{STATIC_PAGE_KEY_PREFIX}{normalized_key}"
    
    def get_current_checksum(self) -> str:
        """
        Calculate checksum of LocationGroup data to detect changes.
        
        Returns:
            SHA256 hash of current data state
        """
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # Get hash of key fields that affect All Locations display
                cursor.execute("""
                    SELECT COUNT(*), 
                           STRING_AGG(location, ',' ORDER BY location)
                    FROM (
                        SELECT location FROM checker_locationgroup 
                        WHERE location IS NOT NULL
                        ORDER BY location
                        LIMIT 100
                    ) as limited_locations
                """)
                
                result = cursor.fetchone()
                if result:
                    data_signature = f"{result[0]}_{result[1] or ''}"
                    return hashlib.sha256(data_signature.encode()).hexdigest()[:16]
                
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            
        # Fallback to timestamp-based checksum
        return hashlib.sha256(str(int(time.time() / 3600)).encode()).hexdigest()[:16]
    
    def is_cache_valid(self) -> bool:
        """
        Check if cached data is still valid by comparing checksums.
        
        Returns:
            True if cache is valid, False if needs refresh
        """
        try:
            cached_checksum = cache.get(CACHE_CHECKSUM_KEY)
            current_checksum = self.get_current_checksum()
            
            if cached_checksum == current_checksum:
                logger.debug(f"Cache valid - checksum {current_checksum}")
                return True
            else:
                logger.info(f"Cache invalid - checksum changed from {cached_checksum} to {current_checksum}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def should_cache_page(self, page: int, status_filter: str = 'all', 
                         auction_filter: str = '', technology_filter: str = '',
                         company_filter: str = '') -> bool:
        """
        Determine if a page should be cached based on access patterns.
        
        Args:
            page: Page number
            status_filter: Status filter
            auction_filter: Auction filter  
            technology_filter: Technology filter
            company_filter: Company filter
            
        Returns:
            True if page should be cached
        """
        # EMERGENCY: Disable all locations caching to prevent Redis spikes
        # Each page is 6.4MB causing Redis to spike to 80%+
        return False
        
        # Original logic (disabled):
        # Only cache unfiltered A-Z sorted pages (most common case)
        # if (page in PAGES_TO_CACHE and 
        #     status_filter == 'all' and 
        #     not auction_filter and 
        #     not technology_filter and 
        #     not company_filter):
        #     return True
        #     
        # return False
    
    def get_cached_page(self, page: int, per_page: int = 25, 
                       status_filter: str = 'all',
                       auction_filter: str = '',
                       technology_filter: str = '',
                       company_filter: str = '',
                       sort_by: str = 'location',
                       sort_order: str = 'asc') -> Optional[Dict[str, Any]]:
        """
        Retrieve cached page data if available and valid.
        
        Args:
            page: Page number
            per_page: Items per page  
            status_filter: Status filter
            auction_filter: Auction filter
            technology_filter: Technology filter
            company_filter: Company filter
            sort_by: Sort field (location, components, etc.)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Cached page data or None if not available
        """
        self.cache_stats['total_requests'] += 1
        
        # Check if this page should be cached
        if not self.should_cache_page(page, status_filter, auction_filter, 
                                     technology_filter, company_filter):
            logger.debug(f"Page {page} not eligible for caching due to filters")
            self.cache_stats['misses'] += 1
            return None
        
        # Check if cache is still valid
        if not self.is_cache_valid():
            logger.info("Cache invalid - clearing all cached pages")
            self.clear_cache()
            self.cache_stats['misses'] += 1
            return None
        
        # Try to get cached data
        cache_key = self.get_cache_key(page, per_page, status_filter, 
                                      auction_filter, technology_filter, company_filter,
                                      sort_by, sort_order)
        
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache HIT for page {page} - saved database queries")
                self.cache_stats['hits'] += 1
                
                # Update access timestamp
                cached_data['cache_meta']['last_accessed'] = timezone.now().isoformat()
                
                return cached_data
            else:
                logger.debug(f"Cache miss for page {page}")
                self.cache_stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached page {page}: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def cache_page(self, page: int, page_data: Dict[str, Any], 
                  per_page: int = 25, status_filter: str = 'all',
                  auction_filter: str = '', technology_filter: str = '',
                  company_filter: str = '', sort_by: str = 'location',
                  sort_order: str = 'asc') -> bool:
        """
        Cache page data with metadata and versioning.
        
        Args:
            page: Page number
            page_data: Complete page context data
            per_page: Items per page
            status_filter: Status filter
            auction_filter: Auction filter
            technology_filter: Technology filter
            company_filter: Company filter
            sort_by: Sort field (location, components, etc.)
            sort_order: Sort order (asc, desc)
            
        Returns:
            True if caching succeeded
        """
        # Only cache eligible pages
        if not self.should_cache_page(page, status_filter, auction_filter,
                                     technology_filter, company_filter):
            return False
        
        try:
            cache_key = self.get_cache_key(page, per_page, status_filter,
                                          auction_filter, technology_filter, company_filter,
                                          sort_by, sort_order)
            
            # Add cache metadata
            cached_data = {
                'page_data': page_data,
                'cache_meta': {
                    'created_at': timezone.now().isoformat(),
                    'last_accessed': timezone.now().isoformat(),
                    'page': page,
                    'checksum': self.get_current_checksum(),
                    'cache_version': CACHE_VERSION
                }
            }
            
            # Cache the data
            cache.set(cache_key, cached_data, STATIC_PAGE_EXPIRATION)
            
            # Update checksum cache
            cache.set(CACHE_CHECKSUM_KEY, self.get_current_checksum(), STATIC_PAGE_EXPIRATION)
            
            logger.info(f"✅ Cached page {page} - future requests will skip database")
            return True
            
        except Exception as e:
            logger.error(f"Error caching page {page}: {e}")
            return False
    
    def warm_cache(self, pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Pre-warm cache by directly generating page data without going through the view.
        
        Args:
            pages: Specific pages to warm, defaults to PAGES_TO_CACHE
            
        Returns:
            Dictionary with warming results
        """
        if pages is None:
            pages = PAGES_TO_CACHE
        
        logger.info(f"🔥 Starting cache warming for pages {pages}")
        start_time = time.time()
        
        results = {
            'success': [],
            'failed': [],
            'total_time': 0,
            'total_pages': len(pages)
        }
        
        # Import here to avoid circular imports
        from ..models import LocationGroup
        from django.core.paginator import Paginator
        from django.db import connection
        
        for page in pages:
            try:
                page_start = time.time()
                
                # Generate page data directly (similar to view logic but simplified)
                # Get all LocationGroups sorted A-Z
                location_groups = LocationGroup.objects.all().order_by('location')
                
                # Use only the fields needed for display
                optimized_locations = location_groups.only(
                    'id', 'location', 'component_count', 'descriptions', 'technologies', 
                    'companies', 'latitude', 'longitude', 'outward_code', 'is_active', 
                    'auction_years', 'normalized_capacity_mw'
                )
                
                # Paginate
                paginator = Paginator(optimized_locations, ITEMS_PER_PAGE)
                try:
                    page_obj = paginator.page(page)
                except:
                    # Page doesn't exist, skip
                    results['failed'].append({
                        'page': page,
                        'error': 'Page does not exist'
                    })
                    continue
                
                # Get totals with fast SQL
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*), COALESCE(SUM(component_count), 0) FROM checker_locationgroup")
                    result = cursor.fetchone()
                    total_locations = result[0]
                    total_components = result[1]
                
                # Get filters for "all locations" view
                with connection.cursor() as cursor:
                    # Get technologies
                    cursor.execute("""
                        SELECT DISTINCT jsonb_object_keys(technologies) as tech
                        FROM checker_locationgroup 
                        WHERE technologies IS NOT NULL
                        ORDER BY tech
                        LIMIT 200
                    """)
                    technologies = [row[0] for row in cursor.fetchall()]
                    
                    # Get companies
                    cursor.execute("""
                        SELECT DISTINCT jsonb_object_keys(companies) as company
                        FROM checker_locationgroup 
                        WHERE companies IS NOT NULL
                        ORDER BY company
                        LIMIT 2000
                    """)
                    companies = [row[0] for row in cursor.fetchall()]
                    
                    # Get auction years
                    cursor.execute("""
                        SELECT DISTINCT jsonb_array_elements_text(auction_years) as year
                        FROM checker_locationgroup 
                        WHERE auction_years IS NOT NULL
                        ORDER BY year DESC
                        LIMIT 50
                    """)
                    auction_years = [row[0] for row in cursor.fetchall()]
                
                # Build context similar to the main view
                context = {
                    'q': '',
                    'query': '',
                    'page_obj': page_obj,
                    'company_links': [],
                    'sort_by': 'location',
                    'sort_order': 'asc',
                    'per_page': ITEMS_PER_PAGE,
                    'total_components': total_components,
                    'total_locations': total_locations,
                    'locations_on_page': len(page_obj),
                    'api_time': time.time() - page_start,
                    'timings': {'cache_warming': time.time() - page_start},
                    'page': page,
                    'status_filter': 'all',
                    'auction_filter': '',
                    'auction_years': auction_years,
                    'technology_filter': '',
                    'technologies': technologies,
                    'company_filter': '',
                    'companies': companies,
                    'related_info': {},
                    'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
                    'user': None,
                    'search_suggestions': [],
                    'did_you_mean': None,
                }
                
                # Cache this page
                cache_success = self.cache_page(
                    page=page,
                    page_data=context,
                    per_page=ITEMS_PER_PAGE,
                    status_filter='all',
                    auction_filter='',
                    technology_filter='',
                    company_filter=''
                )
                
                if cache_success:
                    results['success'].append({
                        'page': page,
                        'time': time.time() - page_start
                    })
                    logger.info(f"✅ Warmed page {page} in {time.time() - page_start:.3f}s")
                else:
                    results['failed'].append({
                        'page': page,
                        'error': 'Failed to cache page'
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'page': page,
                    'error': str(e)
                })
                logger.error(f"❌ Failed to warm page {page}: {e}")
        
        results['total_time'] = time.time() - start_time
        
        logger.info(f"🔥 Cache warming completed: {len(results['success'])}/{len(pages)} pages in {results['total_time']:.3f}s")
        
        return results
    
    def clear_cache(self, pages: Optional[List[int]] = None) -> int:
        """
        Clear cached pages.
        
        Args:
            pages: Specific pages to clear, None to clear all
            
        Returns:
            Number of pages cleared
        """
        if pages is None:
            pages = PAGES_TO_CACHE
        
        cleared = 0
        
        for page in pages:
            try:
                cache_key = self.get_cache_key(page)
                if cache.get(cache_key):
                    cache.delete(cache_key)
                    cleared += 1
                    logger.debug(f"Cleared cache for page {page}")
            except Exception as e:
                logger.error(f"Error clearing cache for page {page}: {e}")
        
        # Clear checksum cache to force refresh
        cache.delete(CACHE_CHECKSUM_KEY)
        
        logger.info(f"🗑️  Cleared {cleared} cached pages")
        return cleared
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        hit_rate = (self.cache_stats['hits'] / max(1, self.cache_stats['total_requests'])) * 100
        
        return {
            'hit_rate': f"{hit_rate:.1f}%",
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'total_requests': self.cache_stats['total_requests'],
            'cache_version': CACHE_VERSION,
            'is_valid': self.is_cache_valid(),
            'current_checksum': self.get_current_checksum()
        }


# Global instance
static_cache = StaticPageCacheService()