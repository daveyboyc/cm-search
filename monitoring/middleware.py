"""
Django Middleware for Automatic Egress Monitoring
Automatically tracks all HTTP requests/responses
"""
import time
import json
from django.utils.deprecation import MiddlewareMixin
from .egress_monitor import monitor

class EgressMonitoringMiddleware(MiddlewareMixin):
    """Middleware to automatically monitor all HTTP requests and responses"""
    
    def process_request(self, request):
        """Called before view is executed"""
        request._egress_start_time = time.time()
        request._egress_request_size = len(request.body) if hasattr(request, 'body') else 0
    
    def process_response(self, request, response):
        """Called after view is executed"""
        if hasattr(request, '_egress_start_time'):
            # Calculate metrics
            duration = (time.time() - request._egress_start_time) * 1000  # ms
            request_size = getattr(request, '_egress_request_size', 0)
            
            # Get response size
            response_size = 0
            if hasattr(response, 'content'):
                response_size = len(response.content)
            elif hasattr(response, 'streaming_content'):
                # For streaming responses (like static files), don't consume the iterator
                # Just skip or estimate based on content-length header
                content_length = response.get('Content-Length', '0')
                try:
                    response_size = int(content_length)
                except:
                    response_size = 0
            
            # Log the API call
            monitor.log_api_call(
                endpoint=request.path,
                method=request.method,
                request_size=request_size,
                response_size=response_size,
                duration=duration
            )
            
            # Alert for large responses
            if response_size > 5 * 1024 * 1024:  # 5MB
                monitor.logger.warning(
                    f"LARGE RESPONSE ALERT: {request.method} {request.path} "
                    f"returned {response_size / 1024 / 1024:.2f}MB"
                )
        
        return response


class DatabaseQueryMonitoringMiddleware(MiddlewareMixin):
    """Middleware to monitor database queries"""
    
    def process_request(self, request):
        """Reset query count at start of request"""
        request._egress_db_queries = 0
        request._egress_db_bytes = 0
    
    def process_response(self, request, response):
        """Log database usage for this request"""
        if hasattr(request, '_egress_db_queries'):
            from django.db import connection
            
            # Get number of queries
            query_count = len(connection.queries) if hasattr(connection, 'queries') else 0
            
            if query_count > 0:
                # Estimate total query response size
                estimated_bytes = query_count * 1000  # Rough estimate: 1KB per query
                
                monitor.log_supabase_query(
                    query=f"Request: {request.method} {request.path}",
                    response_size=estimated_bytes,
                    duration=0
                )
                
                # Alert for query-heavy requests
                if query_count > 20:
                    monitor.logger.warning(
                        f"HIGH QUERY COUNT: {request.method} {request.path} "
                        f"executed {query_count} database queries"
                    )
        
        return response