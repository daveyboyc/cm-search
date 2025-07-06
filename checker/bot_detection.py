"""
Bot detection and handling utilities for SEO optimization
"""
import re
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

# Known bot user agents that hit heavy endpoints
BOT_USER_AGENTS = [
    'meta-externalagent',
    'facebookexternalhit', 
    'amazonbot',
    'googlebot',
    'bingbot',
    'slurp',
    'duckduckbot',
    'baiduspider',
    'yandexbot',
    'twitterbot',
    'linkedinbot',
    'whatsapp',
    'telegram',
    # AI crawlers
    'gptbot',
    'chatgpt-user',
    'claude-web',
    'anthropic',
    'perplexitybot',
    'bytespider',  # TikTok/ByteDance
    'applebot',
    'ia_archiver'  # Internet Archive
]

def is_bot_request(request):
    """
    Detect if request is from a bot based on user agent
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Check for known bot patterns
    for bot_pattern in BOT_USER_AGENTS:
        if bot_pattern in user_agent:
            return True, bot_pattern
    
    # Check for common bot patterns
    bot_indicators = ['bot', 'crawler', 'spider', 'scraper']
    for indicator in bot_indicators:
        if indicator in user_agent:
            return True, 'unknown_bot'
    
    return False, None

def get_bot_response_type(request):
    """
    Determine what type of response to send to bots
    """
    is_bot, bot_type = is_bot_request(request)
    
    if not is_bot:
        return 'normal'
    
    # Heavy bots get lightweight responses
    heavy_bots = ['meta-externalagent', 'amazonbot', 'facebookexternalhit']
    if bot_type in heavy_bots:
        return 'lightweight'
    
    # Search engine bots get redirected to minimal SEO endpoints
    search_bots = ['googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider', 'yandexbot']
    if bot_type in search_bots:
        return 'seo_optimized'
    
    # AI crawlers get lightweight responses (not full SEO redirect)
    ai_crawlers = ['gptbot', 'chatgpt-user', 'claude-web', 'anthropic', 'perplexitybot', 'bytespider']
    if bot_type in ai_crawlers:
        return 'lightweight'
    
    # Other bots get standard response
    return 'normal'

def create_lightweight_response(request, data_context):
    """
    Create a lightweight HTML response for heavy bots
    Serves list view instead of heavy map view
    """
    # Create minimal HTML with essential SEO data
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data_context.get('title', 'Capacity Market Data')}</title>
    <meta name="description" content="{data_context.get('description', 'UK Capacity Market data and components')}">
    <link rel="canonical" href="{request.build_absolute_uri()}">
</head>
<body>
    <h1>{data_context.get('title', 'Capacity Market Data')}</h1>
    <p>{data_context.get('description', 'UK Capacity Market component data')}</p>
    
    <div class="lightweight-list">"""
    
    # Add essential data in list format (lightweight)
    items = data_context.get('items', [])
    for item in items[:50]:  # Limit to 50 items for bots
        html_content += f"""
        <div class="item">
            <h3>{item.get('title', 'Item')}</h3>
            <p>{item.get('description', '')}</p>
            <p>Location: {item.get('location', 'N/A')}</p>
            <p>Capacity: {item.get('capacity', 'N/A')}</p>
        </div>"""
    
    html_content += """
    </div>
    
    <footer>
        <p>UK Capacity Market Data - Lightweight Bot View</p>
    </footer>
</body>
</html>"""
    
    response = HttpResponse(html_content, content_type='text/html')
    response['X-Bot-Response'] = 'lightweight'
    return response

def log_bot_request(request, bot_type, response_type):
    """
    Log bot requests for monitoring
    """
    import logging
    logger = logging.getLogger(__name__)
    
    path = request.path
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:100]
    
    logger.info(f"🤖 BOT REQUEST: {bot_type} -> {path} (response: {response_type}) UA: {user_agent}")