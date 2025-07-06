"""
Middleware to block aggressive bots while allowing SEO crawlers
"""
from django.http import HttpResponseForbidden, HttpResponse
import time

class BotBlockerMiddleware:
    """Block aggressive bots that cause high server load, but allow SEO crawlers"""
    
    # Aggressive bots that cause performance issues
    BLOCKED_USER_AGENTS = [
        'ClaudeBot',
        'GPTBot', 
        'ChatGPT-User',
        'CCBot',
        'Bytespider',
    ]
    
    # Good SEO crawlers to allow (with rate limiting)
    SEO_CRAWLERS = [
        'Googlebot',
        'Bingbot', 
        'DuckDuckBot',
        'facebookexternalhit',
        'meta-externalagent',  # Facebook's crawler that hit you yesterday
        'Amazonbot',           # Amazon's crawler that hit you yesterday
        'Twitterbot',
        'LinkedInBot',
        'Slackbot',
        'WhatsApp',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.crawler_requests = {}  # Simple in-memory rate limiting

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        client_ip = self.get_client_ip(request)
        
        # Block aggressive bots completely
        for bot in self.BLOCKED_USER_AGENTS:
            if bot in user_agent:
                return HttpResponseForbidden(
                    "Bot access blocked. Please respect robots.txt and crawl-delay directives."
                )
        
        # Rate limit SEO crawlers (allow but slow them down)
        for crawler in self.SEO_CRAWLERS:
            if crawler in user_agent:
                if self.is_rate_limited(client_ip, crawler):
                    # Return 429 Too Many Requests with Retry-After header
                    response = HttpResponse(
                        "Rate limited. Please respect crawl-delay in robots.txt.", 
                        status=429
                    )
                    response['Retry-After'] = '10'  # 10 seconds
                    return response
                break
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_rate_limited(self, ip, crawler):
        """Simple rate limiting: max 1 request per 10 seconds per crawler"""
        key = f"{ip}:{crawler}"
        now = time.time()
        
        # Clean old entries (older than 1 minute)
        self.crawler_requests = {
            k: v for k, v in self.crawler_requests.items() 
            if now - v < 60
        }
        
        # Check if this crawler made a recent request
        if key in self.crawler_requests:
            last_request = self.crawler_requests[key]
            if now - last_request < 10:  # 10 second delay
                return True
        
        # Record this request
        self.crawler_requests[key] = now
        return False