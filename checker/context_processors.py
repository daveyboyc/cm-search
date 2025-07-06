from django.conf import settings

def is_premium_page(request):
    """Context processor to check if current page is a premium/map page"""
    premium_url_names = [
        'search_map_view',
        'map_view', 
        'technology_map_results_view',
        'company_map_results_view',
        'map_search_view',
        'map_search_test',
        'technology_detail_map',
        'company_detail_map',
    ]
    
    is_premium = False
    if request.resolver_match:
        is_premium = request.resolver_match.url_name in premium_url_names
    
    # Also check if path contains '/map'
    if not is_premium:
        is_premium = '/map' in request.path
    
    return {
        'is_premium_page': is_premium
    }