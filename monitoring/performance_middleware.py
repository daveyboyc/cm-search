"""
Performance optimization middleware for cache headers and response optimization
"""
import time
import hashlib
from datetime import datetime
from django.utils.cache import patch_cache_control
from django.http import HttpResponse, HttpResponseNotModified
from django.utils.http import http_date

class PerformanceOptimizationMiddleware:
    """Middleware to add performance optimizations like cache headers"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Generate ETag based on content
        if hasattr(response, 'content') and response.content:
            etag = hashlib.md5(response.content).hexdigest()
            response['ETag'] = f'"{etag}"'
            
            # Check if client has current version
            if request.META.get('HTTP_IF_NONE_MATCH') == f'"{etag}"':
                return HttpResponseNotModified()
        
        # Add Last-Modified header (current time for dynamic content)
        response['Last-Modified'] = http_date()
        
        # Add cache headers for static content
        if request.path.startswith('/static/'):
            # Cache static files for 30 days
            patch_cache_control(response, max_age=2592000, public=True)
            
        # Add cache headers for API responses
        elif request.path.startswith('/api/'):
            # Cache API responses for 5 minutes
            patch_cache_control(response, max_age=300, public=True)
            
        # Add cache headers for search results and detail pages
        elif any(path_part in request.path for path_part in ['search', 'company', 'technology', 'component', 'location']):
            # Cache search results and detail pages for 10 minutes
            patch_cache_control(response, max_age=600, public=True)
            
        # Add performance headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        
        return response

class ResponseCompressionMiddleware:
    """Middleware to ensure proper compression for large responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Ensure large responses are marked for compression
        if hasattr(response, 'content'):
            content_length = len(response.content)
            if content_length > 1024:  # Compress responses > 1KB
                response['Vary'] = 'Accept-Encoding'
                
        return response