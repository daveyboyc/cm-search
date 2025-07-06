from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware to enable maintenance mode for the entire site.
    
    When MAINTENANCE_MODE is True, all requests are redirected to the maintenance page
    except for:
    - Requests from allowed IP addresses (defined in MAINTENANCE_ALLOWED_IPS)
    - Static files and media files
    - Admin requests (so you can still manage the site)
    - The maintenance page itself (to avoid infinite redirects)
    """
    
    def process_request(self, request):
        # Fast check - cache the maintenance mode setting to avoid repeated getattr calls
        if not hasattr(self, '_maintenance_mode_cached'):
            self._maintenance_mode_cached = getattr(settings, 'MAINTENANCE_MODE', False)
            
        if not self._maintenance_mode_cached:
            return None
            
        # Get client IP address
        client_ip = self.get_client_ip(request)
        
        # Check if IP is allowed to bypass maintenance mode
        allowed_ips = getattr(settings, 'MAINTENANCE_ALLOWED_IPS', [])
        if client_ip in allowed_ips:
            logger.info(f"Maintenance mode bypassed for allowed IP: {client_ip}")
            return None
        
        # Allow access to specific paths even during maintenance
        path = request.path_info
        
        # Allow access to:
        # - Static files
        # - Media files  
        # - Admin panel (so you can disable maintenance mode)
        # - Maintenance page itself
        exempt_paths = [
            '/static/',
            '/media/',
            '/admin/',
            '/maintenance/',
        ]
        
        for exempt_path in exempt_paths:
            if path.startswith(exempt_path):
                return None
        
        # Log maintenance mode access attempt
        logger.info(f"Maintenance mode active - blocking request from {client_ip} to {path}")
        
        # Render maintenance page
        try:
            # Use cached content if available to avoid file I/O on every request
            if not hasattr(self, '_maintenance_content'):
                import os
                maintenance_path = os.path.join(settings.BASE_DIR.parent, 'static', 'maintenance.html')
                with open(maintenance_path, 'r', encoding='utf-8') as f:
                    self._maintenance_content = f.read()
            return HttpResponse(self._maintenance_content, content_type='text/html', status=503)
        except FileNotFoundError:
            # Fallback to template rendering
            try:
                return render(request, 'maintenance.html', status=503)
            except Exception as e:
                logger.error(f"Error rendering maintenance page: {e}")
                # Final fallback to simple HTTP response
                return HttpResponse(
                    '<h1>Site Under Maintenance</h1>'
                    '<p>We are currently performing scheduled maintenance. Please try again later.</p>',
                    status=503,
                    content_type='text/html'
                )
    
    def get_client_ip(self, request):
        """
        Get the client's IP address from the request.
        Handles cases where the request comes through a proxy.
        """
        # Check for IP in various headers (for proxies/load balancers)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            # Fall back to REMOTE_ADDR
            ip = request.META.get('REMOTE_ADDR', '')
            
        return ip