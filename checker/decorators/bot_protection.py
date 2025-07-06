"""
Bot protection decorators for rate limiting and lightweight responses
"""
from functools import wraps
from django.http import HttpResponse
from django_ratelimit.decorators import ratelimit
from django_ratelimit.core import is_ratelimited
from django.core.cache import cache
import time
import logging

from ..bot_detection import is_bot_request, get_bot_response_type, create_lightweight_response, log_bot_request
from django.shortcuts import redirect
from django.urls import reverse
import re

logger = logging.getLogger(__name__)

def bot_rate_limit(key='ip', rate='10/m', method=['GET', 'POST']):
    """
    Apply rate limiting specifically for bots
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            is_bot, bot_type = is_bot_request(request)
            
            if is_bot:
                # Apply stricter rate limiting for bots
                was_limited = is_ratelimited(
                    request=request,
                    group=f'bot_{view_func.__name__}',
                    fn=view_func,
                    key=lambda group, request: request.META.get('REMOTE_ADDR'),
                    rate=rate,
                    method=method,
                    increment=True
                )
                
                if was_limited:
                    logger.warning(f"🚫 BOT RATE LIMITED: {bot_type} from {request.META.get('REMOTE_ADDR')} on {request.path}")
                    return HttpResponse(
                        "Rate limit exceeded. Please slow down your requests.",
                        status=429,
                        content_type='text/plain'
                    )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def bot_lightweight_response(view_func):
    """
    Serve lightweight responses to heavy bots while maintaining SEO
    Redirects search engine bots to ultra-minimal SEO endpoints
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_bot, bot_type = is_bot_request(request)
        response_type = get_bot_response_type(request)
        
        # Log bot requests for monitoring
        if is_bot:
            log_bot_request(request, bot_type, response_type)
        
        # Serve lightweight content for search engine bots (NO REDIRECT)
        # Skip optimization for component_detail and location_detail since they have custom bot templates
        if (response_type == 'seo_optimized' and 'googlebot' in bot_type and 
            view_func.__name__ not in ['get_component_details', 'location_detail'] and
            '/component/' not in request.path and '/location/' not in request.path):
            # Get the normal response first
            response = view_func(request, *args, **kwargs)
            # Strip heavy elements but keep same URL
            lightweight_response = create_bot_optimized_response(request, response, view_func, *args, **kwargs)
            if lightweight_response:
                logger.info(f"🤖 LIGHTWEIGHT CONTENT: {bot_type} on same URL (saved ~90% bandwidth)")
                return lightweight_response
        
        # Serve lightweight response for heavy bots
        if response_type == 'lightweight':
            # Create a simplified context for lightweight response
            try:
                # Get minimal data for the view
                context = create_lightweight_context(request, view_func, *args, **kwargs)
                return create_lightweight_response(request, context)
            except Exception as e:
                logger.error(f"Error creating lightweight response: {e}")
                # Fall back to normal response but add warning
                response = view_func(request, *args, **kwargs)
                response['X-Bot-Fallback'] = 'lightweight_failed'
                return response
        
        # Normal response for humans and SEO bots
        response = view_func(request, *args, **kwargs)
        
        # Add headers for monitoring
        if is_bot:
            response['X-Bot-Type'] = bot_type
            response['X-Response-Type'] = response_type
        
        return response
    
    return wrapper

def create_lightweight_context(request, view_func, *args, **kwargs):
    """
    Create a lightweight context for bot responses
    Extract essential data without heavy queries
    """
    view_name = view_func.__name__
    
    if 'technology' in view_name:
        technology_name = kwargs.get('technology_name', 'Unknown Technology')
        return {
            'title': f"{technology_name} - UK Capacity Market",
            'description': f"Capacity market components using {technology_name} technology",
            'items': get_lightweight_technology_items(technology_name)
        }
    
    elif 'company' in view_name:
        company_name = kwargs.get('company_name', 'Unknown Company')
        return {
            'title': f"{company_name} - UK Capacity Market",
            'description': f"Capacity market components for {company_name}",
            'items': get_lightweight_company_items(company_name)
        }
    
    else:
        return {
            'title': 'UK Capacity Market Data',
            'description': 'UK Capacity Market component information',
            'items': []
        }

def get_lightweight_technology_items(technology_name):
    """
    Get lightweight technology data for bots (minimal DB queries)
    """
    from ..models import Component
    
    # Simple query with limit to prevent heavy database load
    components = Component.objects.filter(
        technology__icontains=technology_name
    ).select_related().only(
        'location', 'company_name', 'delivery_year', 'derated_capacity_mw'
    )[:25]  # Limit to 25 items
    
    items = []
    for component in components:
        items.append({
            'title': f"{component.company_name or 'Unknown'} - {component.location or 'Unknown Location'}",
            'description': f"{technology_name} capacity market component",
            'location': component.location or 'Not specified',
            'capacity': f"{component.derated_capacity_mw or 0} MW" if component.derated_capacity_mw else 'Not specified',
            'delivery_year': component.delivery_year or 'Not specified'
        })
    
    return items

def get_lightweight_company_items(company_name):
    """
    Get lightweight company data for bots (minimal DB queries)
    """
    from ..models import Component
    import urllib.parse
    
    # Decode company name and normalize
    company_display = urllib.parse.unquote(company_name)
    
    # Simple query with limit
    components = Component.objects.filter(
        company_name__icontains=company_display
    ).select_related().only(
        'location', 'technology', 'delivery_year', 'derated_capacity_mw'
    )[:25]  # Limit to 25 items
    
    items = []
    for component in components:
        items.append({
            'title': f"{component.location or 'Unknown Location'} - {component.technology or 'Unknown Technology'}",
            'description': f"Capacity market component for {company_display}",
            'location': component.location or 'Not specified',
            'capacity': f"{component.derated_capacity_mw or 0} MW" if component.derated_capacity_mw else 'Not specified',
            'technology': component.technology or 'Not specified'
        })
    
    return items

def get_seo_redirect(request, view_func, *args, **kwargs):
    """
    Determine if bot should be redirected to minimal SEO endpoint
    """
    view_name = view_func.__name__
    
    # Redirect company views to minimal SEO endpoints
    if 'company' in view_name and 'company_name' in kwargs:
        company_name = kwargs.get('company_name')
        return reverse('company_seo_minimal', kwargs={'company_name': company_name})
    
    # Redirect technology views to minimal SEO endpoints
    if 'technology' in view_name and 'technology_name' in kwargs:
        technology_name = kwargs.get('technology_name')
        return reverse('technology_seo_minimal', kwargs={'technology_name': technology_name})
    
    # Redirect location views to minimal SEO endpoints
    if 'location' in view_name:
        # Handle both location_group_id and location_id parameters
        location_id = kwargs.get('location_group_id') or kwargs.get('location_id')
        if location_id:
            return reverse('location_seo_minimal', kwargs={'location_group_id': location_id})
    
    # Redirect component views to minimal SEO endpoints
    if 'component' in view_name:
        # Handle both component_id and pk parameters
        component_id = kwargs.get('component_id') or kwargs.get('pk')
        if component_id:
            return reverse('component_seo_minimal', kwargs={'component_id': component_id})
    
    # Special case for CMU detail views
    if 'cmu' in view_name and 'cmu_id' in kwargs:
        cmu_id = kwargs.get('cmu_id')
        return reverse('cmu_seo_minimal', kwargs={'cmu_id': cmu_id})
    
    # Redirect search views to minimal SEO endpoints
    if 'search' in view_name and request.GET.get('q'):
        return reverse('search_seo_minimal') + f"?q={request.GET.get('q')}"
    
    return None

def create_bot_optimized_response(request, response, view_func, *args, **kwargs):
    """
    Create a bot-optimized version of the response by stripping heavy elements
    Same URL, same content structure, just much lighter for search engines
    """
    try:
        if hasattr(response, 'content'):
            html_content = response.content.decode('utf-8')
            
            # Use regex to remove heavy elements that bots don't need
            optimized_html = html_content
            
            # Remove JavaScript (all <script> tags except JSON-LD structured data)
            optimized_html = re.sub(r'<script(?![^>]*type=["\']application/ld\+json["\'])[^>]*>.*?</script>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove CSS files and inline styles more aggressively
            optimized_html = re.sub(r'<link[^>]*rel=["\']stylesheet["\'][^>]*>', '', optimized_html, flags=re.IGNORECASE)
            optimized_html = re.sub(r'<style[^>]*>.*?</style>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            optimized_html = re.sub(r'style=["\'][^"\']*["\']', '', optimized_html, flags=re.IGNORECASE)  # Remove inline styles
            
            # Remove heavy interactive elements
            optimized_html = re.sub(r'<canvas[^>]*>.*?</canvas>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            optimized_html = re.sub(r'<form[^>]*>.*?</form>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            optimized_html = re.sub(r'<input[^>]*>', '', optimized_html, flags=re.IGNORECASE)
            optimized_html = re.sub(r'<button[^>]*>.*?</button>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove elements by class (approximate matching) - expanded list
            heavy_classes = [
                'map-container', 'google-maps', 'pagination', 'btn', 'sidebar', 
                'loading-spinner', 'chart-container', 'modal', 'dropdown', 'navbar',
                'footer', 'theme-switcher', 'fullscreen-toggle', 'map-info-panel'
            ]
            for class_name in heavy_classes:
                # Remove divs/elements with these classes
                pattern = rf'<[^>]*class=["\'][^"\']*{class_name}[^"\']*["\'][^>]*>.*?</[^>]+>'
                optimized_html = re.sub(pattern, '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove background images and large images
            optimized_html = re.sub(r'<img[^>]*src=["\'][^"\']*background[^"\']*["\'][^>]*>', '', optimized_html, flags=re.IGNORECASE)
            optimized_html = re.sub(r'<img[^>]*src=["\'][^"\']*\.(jpeg|jpg|png)["\'][^>]*>', '', optimized_html, flags=re.IGNORECASE)
            
            # Remove inline event handlers
            optimized_html = re.sub(r'on\w+=["\'][^"\']*["\']', '', optimized_html, flags=re.IGNORECASE)
            
            # Remove CSS classes to reduce size
            optimized_html = re.sub(r'class=["\'][^"\']*["\']', '', optimized_html, flags=re.IGNORECASE)
            
            # Add bot-specific meta tag in head
            if '<head>' in optimized_html:
                bot_meta = '<meta name="robots" content="index,follow"><!-- Bot-optimized version: ~95% lighter -->'
                optimized_html = optimized_html.replace('<head>', f'<head>\n{bot_meta}')
            
            # Create new response with optimized content
            new_response = HttpResponse(optimized_html, content_type='text/html')
            
            # Copy important headers
            if hasattr(response, 'status_code'):
                new_response.status_code = response.status_code
            
            # Add bot-specific headers for monitoring
            new_response['X-Bot-Optimized'] = 'true'
            new_response['X-Original-Size'] = str(len(html_content))
            new_response['X-Optimized-Size'] = str(len(optimized_html))
            new_response['Cache-Control'] = 'public, max-age=3600'
            
            # Log the optimization
            original_size = len(html_content)
            optimized_size = len(optimized_html)
            savings = ((original_size - optimized_size) / original_size) * 100
            logger.info(f"📦 BOT OPTIMIZATION: {original_size:,} → {optimized_size:,} bytes ({savings:.1f}% reduction)")
            
            return new_response
            
    except Exception as e:
        logger.error(f"Error creating bot-optimized response: {e}")
        return None
    
    return None

# Combined decorator for easy application
def bot_protected_view(rate='10/m'):
    """
    Combined decorator applying both rate limiting and lightweight responses
    """
    def decorator(view_func):
        @bot_rate_limit(rate=rate)
        @bot_lightweight_response
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator