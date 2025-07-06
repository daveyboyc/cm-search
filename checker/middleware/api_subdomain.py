"""
Middleware to handle API subdomain routing
Detects api.capacitymarket.co.uk and serves API responses
"""
from django.http import JsonResponse
from django.urls import resolve, reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from ..views_api import api_search, api_root, api_docs, api_health

logger = logging.getLogger(__name__)

class APISubdomainMiddleware:
    """
    Middleware to handle API subdomain requests
    Routes api.capacitymarket.co.uk requests to API views
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is an API subdomain request
        host = request.get_host().lower()
        
        if host.startswith('api.'):
            return self.handle_api_request(request)
        
        # Normal processing for main domain
        response = self.get_response(request)
        return response
    
    def handle_api_request(self, request):
        """Handle requests to the API subdomain"""
        path = request.path.lower()
        
        # Log request details for debugging
        logger.info(f"API subdomain request: {request.method} {path}")
        logger.info(f"Query string: {request.GET.urlencode()}")
        logger.info(f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'None')}")
        logger.info(f"Accept: {request.META.get('HTTP_ACCEPT', 'None')}")
        
        # Route API requests to appropriate views
        try:
            # Force all /search requests to go to api_search regardless of case or trailing slash
            if 'search' in path:
                logger.info(f"Routing to api_search for path: {path}")
                return api_search(request)
            elif path == '/' or path == '':
                return api_root(request)
            elif path == '/docs/' or path == '/docs':
                return api_docs(request)
            elif path == '/health/' or path == '/health':
                return api_health(request)
            else:
                # Unknown API endpoint
                response_data = {
                    'error': 'Endpoint not found',
                    'path': path,
                    'available_endpoints': {
                        '/': 'API root with endpoint list',
                        '/search/': 'Search capacity market data',
                        '/docs/': 'API documentation',
                        '/health/': 'API health check'
                    },
                    'examples': [
                        'https://api.capacitymarket.co.uk/',
                        'https://api.capacitymarket.co.uk/search/?q=battery',
                        'https://api.capacitymarket.co.uk/docs/'
                    ]
                }
                
                response = JsonResponse(response_data, status=404)
                response['Access-Control-Allow-Origin'] = '*'
                response['Cache-Control'] = 'public, max-age=300'
                return response
                
        except Exception as e:
            logger.exception(f"Error handling API request: {str(e)}")
            response_data = {
                'error': 'Internal server error',
                'message': str(e),
                'path': path
            }
            
            response = JsonResponse(response_data, status=500)
            response['Access-Control-Allow-Origin'] = '*'
            return response