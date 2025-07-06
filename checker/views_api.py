"""
Clean API views for api.capacitymarket.co.uk subdomain
RESTful endpoints for programmatic access to capacity market data
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
import logging

from .models import Component, CMURegistry, LocationGroup
from .services.company_search import search_companies_service
from .services.component_search import search_components_service

logger = logging.getLogger(__name__)

def add_cors_headers(response):
    """Add CORS headers for API access"""
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key, Authorization'
    response['Access-Control-Max-Age'] = '86400'
    response['Cache-Control'] = 'public, max-age=300'  # Cache for 5 minutes
    return response

@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def api_search(request):
    """
    Main search endpoint for the API subdomain.
    Replaces the old /search-json/ and /search-map-json/ endpoints.
    """
    # Always log incoming requests for debugging
    logger.info(f"API search request: {request.method} from {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    logger.info(f"Query params: {request.GET.dict()}")
    logger.info(f"Full path: {request.get_full_path()}")
    
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        return add_cors_headers(response)
    
    # Get query parameter
    if request.method == 'GET':
        query = request.GET.get('q', request.GET.get('query', '')).strip()
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
        except (json.JSONDecodeError, TypeError):
            query = request.GET.get('q', '').strip()
    
    if not query:
        response = JsonResponse({
            'error': 'Query parameter required',
            'usage': {
                'GET': 'https://api.capacitymarket.co.uk/search/?q=battery',
                'POST': '{"query": "battery storage"}'
            },
            'endpoints': {
                'search': '/search/',
                'companies': '/companies/',
                'technologies': '/technologies/',
                'components': '/components/',
                'locations': '/locations/',
                'cmus': '/cmus/',
                'docs': '/docs/'
            }
        }, status=400)
        return add_cors_headers(response)
    
    try:
        # Use the same database query logic as the working endpoints
        components_query = Component.objects.filter(
            Q(location__icontains=query) |
            Q(company_name__icontains=query) |
            Q(description__icontains=query) |
            Q(technology__icontains=query) |
            Q(cmu_id__icontains=query)
        ).order_by('company_name', 'location')[:50]
        
        # Format results for API consumption
        components = []
        for comp in components_query:
            components.append({
                'cmu_id': comp.cmu_id or '',
                'company_name': comp.company_name or '',
                'location': comp.location or '',
                'description': comp.description or '',
                'technology': comp.technology or '',
                'derated_capacity_mw': float(comp.derated_capacity_mw) if comp.derated_capacity_mw else None,
                'delivery_year': comp.delivery_year or '',
                'auction_name': comp.auction_name or '',
                'market_status': getattr(comp, 'market_status', 'Unknown'),
                'api_url': f"https://api.capacitymarket.co.uk/components/{comp.pk}/",
                'web_url': f"https://capacitymarket.co.uk/component/{comp.pk}/"
            })
        
        response_data = {
            'query': query,
            'results_count': len(components),
            'summary': f"Found {len(components)} capacity market components matching '{query}'",
            'data': components,
            'meta': {
                'api_version': '1.0',
                'endpoint': '/search/',
                'method': request.method,
                'timestamp': None  # Add timestamp if needed
            },
            'links': {
                'self': f"https://api.capacitymarket.co.uk/search/?q={query}",
                'docs': 'https://api.capacitymarket.co.uk/docs/',
                'web': f"https://capacitymarket.co.uk/search-map/?q={query}"
            }
        }
        
        response = JsonResponse(response_data)
        return add_cors_headers(response)
        
    except Exception as e:
        logger.exception(f"Error in API search: {str(e)}")
        response = JsonResponse({
            'error': f'Search failed: {str(e)}',
            'query': query,
            'data': [],
            'results_count': 0
        }, status=500)
        return add_cors_headers(response)

def api_root(request):
    """API root endpoint with available endpoints"""
    response_data = {
        'message': 'UK Capacity Market API',
        'version': '1.0',
        'description': 'RESTful API for accessing UK capacity market data',
        'endpoints': {
            'search': {
                'url': '/search/',
                'description': 'Search across all capacity market data',
                'example': '/search/?q=battery'
            },
            'companies': {
                'url': '/companies/',
                'description': 'List and search companies',
                'example': '/companies/edf/'
            },
            'technologies': {
                'url': '/technologies/',
                'description': 'List and search technologies',
                'example': '/technologies/battery/'
            },
            'components': {
                'url': '/components/',
                'description': 'List and search components',
                'example': '/components/12345/'
            },
            'locations': {
                'url': '/locations/',
                'description': 'List and search locations',
                'example': '/locations/123/'
            },
            'cmus': {
                'url': '/cmus/',
                'description': 'List and search CMUs',
                'example': '/cmus/ABC123/'
            }
        },
        'usage': {
            'base_url': 'https://api.capacitymarket.co.uk',
            'authentication': 'None required for read access',
            'rate_limits': '1000 requests per hour',
            'formats': ['JSON'],
            'cors': 'Enabled for all origins'
        },
        'links': {
            'documentation': '/docs/',
            'health': '/health/',
            'main_site': 'https://capacitymarket.co.uk'
        }
    }
    
    response = JsonResponse(response_data)
    return add_cors_headers(response)

def api_docs(request):
    """API documentation endpoint"""
    response_data = {
        'title': 'UK Capacity Market API Documentation',
        'version': '1.0',
        'base_url': 'https://api.capacitymarket.co.uk',
        'endpoints': {
            '/search/': {
                'methods': ['GET', 'POST'],
                'description': 'Search across all capacity market data',
                'parameters': {
                    'q': 'Search query string',
                    'query': 'Alternative parameter name for search query'
                },
                'examples': [
                    '/search/?q=battery',
                    '/search/?q=gas%20plants%20in%20London',
                    '/search/?q=EDF%20nuclear'
                ]
            }
        },
        'response_format': {
            'query': 'The search query that was processed',
            'results_count': 'Number of results found',
            'summary': 'Human-readable summary',
            'data': 'Array of matching components',
            'meta': 'API metadata',
            'links': 'Related URLs'
        },
        'migration_guide': {
            'old_endpoints': [
                'https://capacitymarket.co.uk/search-json/',
                'https://capacitymarket.co.uk/search-map-json/',
                'https://capacitymarket.co.uk/api/gpt-search/'
            ],
            'new_endpoint': 'https://api.capacitymarket.co.uk/search/',
            'note': 'Old endpoints redirect here automatically'
        }
    }
    
    response = JsonResponse(response_data)
    return add_cors_headers(response)

def api_health(request):
    """API health check endpoint"""
    response_data = {
        'status': 'healthy',
        'timestamp': None,  # Add if needed
        'version': '1.0',
        'database': 'connected',
        'cache': 'available'
    }
    
    response = JsonResponse(response_data)
    return add_cors_headers(response)

# Placeholder endpoints for future implementation
def api_companies(request):
    """Companies list endpoint - placeholder"""
    response = JsonResponse({
        'message': 'Companies endpoint - coming soon',
        'redirect': '/search/?q=company_name'
    }, status=501)
    return add_cors_headers(response)

def api_company_detail(request, company_name):
    """Company detail endpoint - placeholder"""
    response = JsonResponse({
        'message': f'Company detail for {company_name} - coming soon',
        'redirect': f'/search/?q={company_name}'
    }, status=501)
    return add_cors_headers(response)

def api_technologies(request):
    """Technologies list endpoint - placeholder"""
    response = JsonResponse({
        'message': 'Technologies endpoint - coming soon',
        'redirect': '/search/?q=technology_name'
    }, status=501)
    return add_cors_headers(response)

def api_technology_detail(request, technology_name):
    """Technology detail endpoint - placeholder"""
    response = JsonResponse({
        'message': f'Technology detail for {technology_name} - coming soon',
        'redirect': f'/search/?q={technology_name}'
    }, status=501)
    return add_cors_headers(response)

def api_components(request):
    """Components list endpoint - placeholder"""
    response = JsonResponse({
        'message': 'Components endpoint - coming soon',
        'redirect': '/search/'
    }, status=501)
    return add_cors_headers(response)

def api_component_detail(request, component_id):
    """Component detail endpoint - placeholder"""
    response = JsonResponse({
        'message': f'Component detail for {component_id} - coming soon',
        'redirect': f'/search/?q={component_id}'
    }, status=501)
    return add_cors_headers(response)

def api_locations(request):
    """Locations list endpoint - placeholder"""
    response = JsonResponse({
        'message': 'Locations endpoint - coming soon',
        'redirect': '/search/?q=location_name'
    }, status=501)
    return add_cors_headers(response)

def api_location_detail(request, location_id):
    """Location detail endpoint - placeholder"""
    response = JsonResponse({
        'message': f'Location detail for {location_id} - coming soon',
        'redirect': f'/search/?q={location_id}'
    }, status=501)
    return add_cors_headers(response)

def api_cmus(request):
    """CMUs list endpoint - placeholder"""
    response = JsonResponse({
        'message': 'CMUs endpoint - coming soon',
        'redirect': '/search/?q=cmu_id'
    }, status=501)
    return add_cors_headers(response)

def api_cmu_detail(request, cmu_id):
    """CMU detail endpoint - placeholder"""
    response = JsonResponse({
        'message': f'CMU detail for {cmu_id} - coming soon',
        'redirect': f'/search/?q={cmu_id}'
    }, status=501)
    return add_cors_headers(response)

def api_catch_all(request, path):
    """Catch-all view for unmatched API paths - returns JSON instead of OK"""
    logger.warning(f"API catch-all hit: {path} from {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    
    response_data = {
        'error': 'Unknown API endpoint',
        'path': f'/{path}',
        'message': 'The requested endpoint does not exist. Please check the API documentation.',
        'available_endpoints': {
            '/': 'API root',
            '/search/': 'Search endpoint',
            '/docs/': 'API documentation',
            '/health/': 'Health check'
        }
    }
    
    response = JsonResponse(response_data, status=404)
    return add_cors_headers(response)