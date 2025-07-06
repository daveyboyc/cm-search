"""
Performance monitoring middleware for map page optimization.

This middleware tracks key performance metrics for map-related requests
and provides alerting when performance thresholds are exceeded.
"""
import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class MapPerformanceMonitoringMiddleware:
    """
    Middleware to monitor map page performance and cache effectiveness.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.performance_thresholds = {
            'api_response_time': 2.0,  # seconds
            'cache_miss_rate': 0.3,    # 30%
            'large_response_size': 50 * 1024,  # 50KB
            'sequential_api_calls': 5   # number of calls
        }
    
    def __call__(self, request):
        # Skip monitoring for non-map requests
        if not self.is_map_request(request):
            return self.get_response(request)
        
        start_time = time.time()
        
        # Track request start
        request._performance_start = start_time
        request._api_call_count = 0
        request._cache_hits = 0
        request._cache_misses = 0
        
        response = self.get_response(request)
        
        # Calculate metrics
        total_time = time.time() - start_time
        response_size = len(response.content) if hasattr(response, 'content') else 0
        
        # Log performance metrics
        self.log_performance_metrics(request, response, total_time, response_size)
        
        # Check for performance issues
        self.check_performance_alerts(request, total_time, response_size)
        
        return response
    
    def is_map_request(self, request):
        """Determine if this is a map-related request."""
        map_paths = [
            '/api/search-geojson/',
            '/api/batch-geojson/',
            '/api/stream-geojson/',
            '/api/map-data/',
            '/search-map/',
            '/map/',
            '/company-map/',
            '/technology-map/'
        ]
        
        return any(request.path.startswith(path) for path in map_paths)
    
    def log_performance_metrics(self, request, response, total_time, response_size):
        """Log detailed performance metrics."""
        cache_hit_rate = 0
        if hasattr(request, '_cache_hits') and hasattr(request, '_cache_misses'):
            total_cache_requests = request._cache_hits + request._cache_misses
            if total_cache_requests > 0:
                cache_hit_rate = request._cache_hits / total_cache_requests
        
        metrics = {
            'path': request.path,
            'method': request.method,
            'total_time': round(total_time, 3),
            'response_size': response_size,
            'response_size_kb': round(response_size / 1024, 1),
            'api_call_count': getattr(request, '_api_call_count', 0),
            'cache_hits': getattr(request, '_cache_hits', 0),
            'cache_misses': getattr(request, '_cache_misses', 0),
            'cache_hit_rate': round(cache_hit_rate, 2),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100],
            'remote_ip': self.get_client_ip(request)
        }
        
        logger.info(f"🗺️ Map Performance: {metrics['path']} - "
                   f"{metrics['total_time']}s, {metrics['response_size_kb']}KB, "
                   f"{metrics['cache_hits']}/{metrics['cache_misses']} cache hits/misses")
        
        # Store metrics for trend analysis
        self.store_performance_metrics(metrics)
    
    def check_performance_alerts(self, request, total_time, response_size):
        """Check for performance issues and log alerts."""
        alerts = []
        
        # Check response time
        if total_time > self.performance_thresholds['api_response_time']:
            alerts.append(f"Slow response: {total_time:.2f}s (threshold: {self.performance_thresholds['api_response_time']}s)")
        
        # Check response size
        if response_size > self.performance_thresholds['large_response_size']:
            size_kb = response_size / 1024
            threshold_kb = self.performance_thresholds['large_response_size'] / 1024
            alerts.append(f"Large response: {size_kb:.1f}KB (threshold: {threshold_kb:.1f}KB)")
        
        # Check cache miss rate
        if hasattr(request, '_cache_hits') and hasattr(request, '_cache_misses'):
            total_cache_requests = request._cache_hits + request._cache_misses
            if total_cache_requests > 0:
                miss_rate = request._cache_misses / total_cache_requests
                if miss_rate > self.performance_thresholds['cache_miss_rate']:
                    alerts.append(f"High cache miss rate: {miss_rate:.1%} (threshold: {self.performance_thresholds['cache_miss_rate']:.1%})")
        
        # Check API call count
        api_calls = getattr(request, '_api_call_count', 0)
        if api_calls > self.performance_thresholds['sequential_api_calls']:
            alerts.append(f"Too many API calls: {api_calls} (threshold: {self.performance_thresholds['sequential_api_calls']})")
        
        # Log alerts
        if alerts:
            logger.warning(f"🚨 Map Performance Alert for {request.path}: {'; '.join(alerts)}")
            
            # Store alert for dashboard/monitoring
            self.store_performance_alert(request.path, alerts, {
                'response_time': total_time,
                'response_size': response_size,
                'cache_hits': getattr(request, '_cache_hits', 0),
                'cache_misses': getattr(request, '_cache_misses', 0),
                'api_calls': api_calls
            })
    
    def store_performance_metrics(self, metrics):
        """Store performance metrics for trend analysis."""
        try:
            # Use cache to store recent metrics (could also use database/monitoring service)
            cache_key = f"perf_metrics_{int(time.time() // 60)}"  # 1-minute buckets
            current_metrics = cache.get(cache_key, [])
            current_metrics.append(metrics)
            
            # Keep only last 100 metrics per minute
            if len(current_metrics) > 100:
                current_metrics = current_metrics[-100:]
            
            cache.set(cache_key, current_metrics, 300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {e}")
    
    def store_performance_alert(self, path, alerts, metrics):
        """Store performance alerts for monitoring dashboard."""
        try:
            alert_data = {
                'timestamp': time.time(),
                'path': path,
                'alerts': alerts,
                'metrics': metrics
            }
            
            # Store recent alerts
            alerts_key = "perf_alerts_recent"
            recent_alerts = cache.get(alerts_key, [])
            recent_alerts.append(alert_data)
            
            # Keep only last 50 alerts
            if len(recent_alerts) > 50:
                recent_alerts = recent_alerts[-50:]
            
            cache.set(alerts_key, recent_alerts, 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Failed to store performance alert: {e}")
    
    def get_client_ip(self, request):
        """Get the real client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CacheMonitoringMixin:
    """
    Mixin for views to track cache performance.
    """
    
    def track_cache_hit(self, request):
        """Track a cache hit."""
        if hasattr(request, '_cache_hits'):
            request._cache_hits += 1
        else:
            request._cache_hits = 1
    
    def track_cache_miss(self, request):
        """Track a cache miss."""
        if hasattr(request, '_cache_misses'):
            request._cache_misses += 1
        else:
            request._cache_misses = 1
    
    def track_api_call(self, request):
        """Track an API call."""
        if hasattr(request, '_api_call_count'):
            request._api_call_count += 1
        else:
            request._api_call_count = 1


def get_performance_dashboard_data():
    """
    Get performance data for monitoring dashboard.
    """
    try:
        # Get recent alerts
        alerts = cache.get("perf_alerts_recent", [])
        
        # Get recent metrics (last 5 minutes)
        current_minute = int(time.time() // 60)
        recent_metrics = []
        
        for i in range(5):  # Last 5 minutes
            minute_key = f"perf_metrics_{current_minute - i}"
            minute_metrics = cache.get(minute_key, [])
            recent_metrics.extend(minute_metrics)
        
        # Calculate summary statistics
        if recent_metrics:
            avg_response_time = sum(m['total_time'] for m in recent_metrics) / len(recent_metrics)
            avg_response_size = sum(m['response_size'] for m in recent_metrics) / len(recent_metrics)
            total_cache_hits = sum(m['cache_hits'] for m in recent_metrics)
            total_cache_misses = sum(m['cache_misses'] for m in recent_metrics)
            
            cache_hit_rate = 0
            if (total_cache_hits + total_cache_misses) > 0:
                cache_hit_rate = total_cache_hits / (total_cache_hits + total_cache_misses)
        else:
            avg_response_time = 0
            avg_response_size = 0
            cache_hit_rate = 0
        
        return {
            'recent_alerts': alerts[-10:],  # Last 10 alerts
            'metrics_summary': {
                'avg_response_time': round(avg_response_time, 3),
                'avg_response_size_kb': round(avg_response_size / 1024, 1),
                'cache_hit_rate': round(cache_hit_rate, 2),
                'total_requests': len(recent_metrics)
            },
            'recent_metrics': recent_metrics[-20:]  # Last 20 requests
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance dashboard data: {e}")
        return {
            'recent_alerts': [],
            'metrics_summary': {},
            'recent_metrics': []
        }