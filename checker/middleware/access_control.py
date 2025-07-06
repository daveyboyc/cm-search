"""
Access Control Middleware for 2-Tier System

Redirects users with expired trials to payment page unless they have full access.
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

# DEBUG: Print to console when middleware is imported
print("🔥 ACCESS CONTROL MIDDLEWARE IMPORTED - THIS SHOULD APPEAR IN LOGS")


class AccessControlMiddleware:
    """
    Middleware to enforce 2-tier access control across the entire site.
    
    - Users with 'trial' access: Full access to all pages
    - Users with 'full' access: Full access to all pages  
    - Users with 'trial_expired' access: Redirected to payment page
    - Unauthenticated users: Allow access to public pages
    """
    
    def __init__(self, get_response):
        print("🚨 MIDDLEWARE __INIT__ CALLED - MIDDLEWARE IS BEING LOADED!")
        self.get_response = get_response
        
        # URLs that should be accessible even for expired trial users
        self.public_urls = [
            '/admin/',
            '/admin/logout/',
            '/accounts/login/', 
            '/accounts/logout/',
            '/accounts/password_reset/',
            '/accounts/password_change/',
            '/accounts/password_change/done/',
            '/login/',
            '/logout/',
            '/accounts/account/',  # Account page for password changes etc
            '/accounts/register/',
            '/accounts/activate/',
            '/accounts/registration-pending/',
            '/accounts/activation-failed/',
            '/accounts/payment-required/',  # MUST be public for subscription-expired users
            '/accounts/payment-selection/',  # MUST be public for subscription-expired users
            '/accounts/initiate-payment/',   # MUST be public for subscription-expired users
            '/accounts/stripe/webhook/',
            '/accounts/stripe-webhook/',
            '/accounts/password-reset/',
            '/accounts/password-reset-done/',
            '/accounts/password-reset-confirm/',
            '/accounts/password-reset-complete/',
            '/trades/',  # Trading board - free to view
            '/location/',  # Location detail pages - accessible via Google search
            '/component/',  # Component detail pages - accessible via Google search
            '/locations/',  # SEO-friendly location URLs and hierarchical component URLs
            '/components/',  # SEO-friendly component URLs
            '/seo/',  # Minimal SEO endpoints for bots
            '/static/',
            '/favicon.ico',
            '/sitemap.xml',
            '/robots.txt',
        ]
        
        # API endpoints that should return JSON errors instead of redirects
        self.api_urls = [
            '/api/',
        ]

    def __call__(self, request):
        # DEBUG: Log all requests to see if middleware is being called for test user
        if request.user.is_authenticated and request.user.email == '5doubow@spamok.com':
            logger.info(f"🔍 ACCESS CONTROL MIDDLEWARE: Processing {request.path} for user {request.user.username}")
            logger.info(f"🔍 REQUEST DETAILS: method={request.method}, authenticated={request.user.is_authenticated}")
        
        # Debug logging for logout attempts
        if 'logout' in request.path:
            logger.info(f"LOGOUT REQUEST: {request.method} {request.path} - User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
        
        # Skip middleware for public URLs, BUT check subscription-expired users first
        if any(request.path.startswith(url) for url in self.public_urls):
            if 'logout' in request.path:
                logger.info(f"LOGOUT ALLOWED: {request.path} is in public_urls")
            
            # Even for public URLs, check if this is a subscription-expired user
            if request.user.is_authenticated:
                try:
                    from checker.access_control import get_user_access_level
                    access_level = get_user_access_level(request.user)
                    
                    # Subscription-expired users get redirected even from public pages
                    if access_level == 'subscription_expired':
                        logger.info(f"🚨 SUBSCRIPTION EXPIRED: User {request.user.username} accessing {request.path}")
                        
                        # Allow access to account page itself and payment pages (don't redirect in a loop)
                        allowed_payment_urls = ['/accounts/account/', '/accounts/payment-required/', '/accounts/payment-selection/', '/accounts/initiate-payment/']
                        if any(request.path.startswith(url) for url in allowed_payment_urls):
                            logger.info(f"✅ ALLOWING ACCESS: {request.path} is a payment/account page (matched: {[url for url in allowed_payment_urls if request.path.startswith(url)]})")
                            return self.get_response(request)
                        
                        logger.info(f"🔄 REDIRECTING: subscription-expired user {request.user.username} from public URL {request.path} to account page")
                        return redirect('accounts:account')
                        
                except Exception as e:
                    logger.error(f"Error checking subscription status on public URL: {e}")
            
            return self.get_response(request)
            
        # Skip middleware for unauthenticated users (they can browse freely)
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Check user access level
        try:
            from checker.access_control import get_user_access_level, start_trial_if_needed
            
            # Start trial if needed
            start_trial_if_needed(request.user)
            
            access_level = get_user_access_level(request.user)
            
            # Allow full access users and active trial users
            if access_level in ['full', 'trial']:
                return self.get_response(request)
                
            # Redirect expired trial users to payment page
            elif access_level == 'trial_expired':
                logger.info(f"Redirecting expired trial user {request.user.username} from {request.path}")
                
                # Return JSON error for API endpoints
                if any(request.path.startswith(url) for url in self.api_urls):
                    return JsonResponse({
                        'error': 'Trial expired',
                        'message': 'Your weekly trial has expired. Please upgrade to continue.',
                        'payment_url': reverse('accounts:payment_selection')
                    }, status=402)
                    
                # Redirect web pages to payment required page
                return redirect('accounts:payment_required')
                
            # Redirect subscription-expired users to account page (no trial available)
            elif access_level == 'subscription_expired':
                logger.info(f"🚨 SUBSCRIPTION EXPIRED (protected): User {request.user.username} accessing {request.path}")
                
                # Return JSON error for API endpoints
                if any(request.path.startswith(url) for url in self.api_urls):
                    return JsonResponse({
                        'error': 'Subscription expired',
                        'message': 'Your £5/year subscription has expired. Please renew to continue. No trial available.',
                        'payment_url': reverse('accounts:account')
                    }, status=402)
                    
                # Redirect ALL non-public pages to account page where they'll see expiry message
                logger.info(f"🔄 REDIRECTING (protected): subscription-expired user {request.user.username} from {request.path} to account page")
                return redirect('accounts:account')
                
            else:
                # Unknown access level - log and allow through
                logger.warning(f"Unknown access level '{access_level}' for user {request.user.username}")
                return self.get_response(request)
                
        except Exception as e:
            logger.error(f"Error in AccessControlMiddleware for user {request.user.username}: {e}")
            # On error, allow through to prevent breaking the site
            return self.get_response(request)