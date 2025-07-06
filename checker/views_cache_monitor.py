"""
Cache monitoring view for static page cache performance.

This view provides real-time statistics about the static page cache
performance, including hit rates, cache validity, and optimization metrics.
"""

import json
import redis
from urllib.parse import urlparse
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from .services.static_page_cache import static_cache, PAGES_TO_CACHE
from django.core.cache import cache


@staff_member_required
@never_cache
def cache_monitor_api(request):
    """
    API endpoint for cache monitoring data.
    
    Returns JSON with current cache statistics and performance metrics.
    """
    try:
        # Get cache statistics
        stats = static_cache.get_cache_stats()
        
        # Get detailed cache information
        cache_details = []
        
        for page in PAGES_TO_CACHE:
            cache_key = static_cache.get_cache_key(page)
            cached_data = cache.get(cache_key)
            
            if cached_data:
                cache_meta = cached_data.get('cache_meta', {})
                cache_details.append({
                    'page': page,
                    'status': 'cached',
                    'created_at': cache_meta.get('created_at'),
                    'last_accessed': cache_meta.get('last_accessed'),
                    'checksum': cache_meta.get('checksum', 'unknown')
                })
            else:
                cache_details.append({
                    'page': page,
                    'status': 'not_cached',
                    'created_at': None,
                    'last_accessed': None,
                    'checksum': None
                })
        
        # Get Redis memory usage statistics
        redis_stats = {}
        try:
            # Get Redis connection using same logic as emergency cleanup
            redis_url = settings.CACHES['default']['LOCATION']
            parsed = urlparse(redis_url)
            r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port,
                password=parsed.password,
                decode_responses=True
            )
            
            # Get memory info
            memory_info = r.info('memory')
            used_memory = memory_info.get('used_memory', 0)
            max_memory = memory_info.get('maxmemory', 0)
            
            if max_memory > 0:
                usage_percent = (used_memory / max_memory) * 100
                redis_stats = {
                    'used_memory_mb': round(used_memory / 1024 / 1024, 2),
                    'max_memory_mb': round(max_memory / 1024 / 1024, 2),
                    'usage_percent': round(usage_percent, 1),
                    'status': 'critical' if usage_percent > 90 else 'warning' if usage_percent > 80 else 'ok'
                }
            else:
                redis_stats = {'error': 'Unable to determine Redis memory limits'}
                
        except Exception as e:
            redis_stats = {'error': f'Redis connection failed: {str(e)}'}
        
        # Calculate performance metrics
        hit_rate_numeric = 0
        if stats['total_requests'] > 0:
            hit_rate_numeric = (stats['hits'] / stats['total_requests']) * 100
        
        # Estimate savings
        estimated_db_queries_saved = stats['hits'] * 10  # Avg 10 queries per page
        estimated_egress_saved_kb = stats['hits'] * 15   # Avg 15KB per page
        estimated_time_saved_ms = stats['hits'] * 200    # Avg 200ms per page
        
        response_data = {
            'cache_stats': stats,
            'cache_details': cache_details,
            'redis_stats': redis_stats,
            'performance_metrics': {
                'hit_rate_numeric': round(hit_rate_numeric, 2),
                'estimated_db_queries_saved': estimated_db_queries_saved,
                'estimated_egress_saved_kb': estimated_egress_saved_kb,
                'estimated_time_saved_ms': estimated_time_saved_ms,
                'cached_pages_count': len([d for d in cache_details if d['status'] == 'cached']),
                'total_monitored_pages': len(PAGES_TO_CACHE)
            },
            'recommendations': get_cache_recommendations(stats, cache_details, redis_stats)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'cache_stats': None
        }, status=500)


@staff_member_required
def cache_monitor_dashboard(request):
    """
    HTML dashboard for cache monitoring.
    
    Provides a user-friendly interface to view cache performance.
    """
    context = {
        'page_title': 'Static Cache Monitor',
        'pages_monitored': PAGES_TO_CACHE,
        'cache_version': static_cache.get_cache_stats().get('cache_version', 'unknown')
    }
    
    return render(request, 'checker/cache_monitor.html', context)


def get_cache_recommendations(stats, cache_details, redis_stats=None):
    """
    Generate recommendations based on cache performance.
    
    Args:
        stats: Cache statistics
        cache_details: Detailed cache information
        redis_stats: Redis memory statistics (optional)
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Check Redis memory usage first (most critical)
    if redis_stats and 'usage_percent' in redis_stats:
        usage_percent = redis_stats['usage_percent']
        if usage_percent > 95:
            recommendations.append("🚨 CRITICAL: Redis memory usage >95% - run emergency cleanup immediately")
        elif usage_percent > 90:
            recommendations.append("⚠️ HIGH: Redis memory usage >90% - consider running emergency cleanup")
        elif usage_percent > 80:
            recommendations.append("⚠️ WARNING: Redis memory usage >80% - monitor closely")
        else:
            recommendations.append(f"✅ Redis memory usage healthy at {usage_percent}%")
    elif redis_stats and 'error' in redis_stats:
        recommendations.append(f"⚠️ Redis monitoring unavailable: {redis_stats['error']}")
    
    # Check hit rate
    if stats['total_requests'] > 10:  # Only if we have enough data
        hit_rate_numeric = (stats['hits'] / stats['total_requests']) * 100
        
        if hit_rate_numeric < 30:
            recommendations.append("❌ Low cache hit rate - consider warming cache manually")
        elif hit_rate_numeric < 60:
            recommendations.append("⚠️ Moderate cache hit rate - monitor for improvements")
        else:
            recommendations.append("✅ Good cache hit rate - optimization working well")
    
    # Check cache validity
    if not stats['is_valid']:
        recommendations.append("🔄 Cache is invalid - data has changed, consider warming")
    
    # Check cached pages
    cached_count = len([d for d in cache_details if d['status'] == 'cached'])
    if cached_count < len(PAGES_TO_CACHE):
        missing_pages = len(PAGES_TO_CACHE) - cached_count
        recommendations.append(f"📄 {missing_pages} pages not cached - run warm_static_cache command")
    
    # Performance recommendations
    if stats['hits'] > 0:
        avg_savings_per_hit = 200  # ms
        total_time_saved = stats['hits'] * avg_savings_per_hit
        if total_time_saved > 60000:  # More than 1 minute saved
            recommendations.append(f"🚀 Great performance impact! Saved ~{total_time_saved/1000:.1f}s total response time")
    
    if not recommendations:
        recommendations.append("✅ Cache performance looks good!")
    
    return recommendations