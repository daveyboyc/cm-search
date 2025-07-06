"""
Test view for unified search and map interface mockup
"""
from django.shortcuts import render
from .decorators.access_required import map_access_required

@map_access_required
def unified_search_map_test(request):
    """
    Test view for the unified search results and map interface.
    This is a mockup with generated test data.
    """
    context = {
        'search_query': request.GET.get('q', 'Test Search'),
    }
    return render(request, 'checker/unified_search_map.html', context)

@map_access_required
def unified_search_map_google_test(request):
    """
    Test view for the unified search results and map interface with Google Maps.
    This is a mockup with generated test data.
    """
    from django.conf import settings
    context = {
        'search_query': request.GET.get('q', 'Test Search'),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'checker/unified_search_map_google.html', context)

@map_access_required
def test_google_maps(request):
    """Test page for Google Maps API"""
    from django.conf import settings
    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'checker/test_google_maps.html', context)

@map_access_required
def search_with_map(request):
    """Search results with integrated map view - matches current search page design"""
    context = {
        'query': request.GET.get('q', 'asda'),
        'sort_by': request.GET.get('sort_by', 'relevance'),
        'sort_order': request.GET.get('sort_order', 'asc'),
        'per_page': request.GET.get('per_page', '25'),
        'total_results': 100,  # Mock data
    }
    return render(request, 'checker/search_with_map.html', context)

@map_access_required
def search_results_with_map(request):
    """Search results with map - full width design with logo header"""
    context = {
        'query': request.GET.get('q', 'asda'),
        'sort_by': request.GET.get('sort_by', 'relevance'),
        'sort_order': request.GET.get('sort_order', 'asc'),
        'per_page': request.GET.get('per_page', '25'),
        'total_results': 100,  # Mock data
    }
    return render(request, 'checker/search_results_with_map.html', context)

@map_access_required
def search_results_with_map_real(request):
    """Search results with map using REAL search data from the component search service"""
    import time
    from django.core.paginator import Paginator
    
    # First, check if we should use location groups
    try:
        from .services.location_group_check import should_use_location_groups
        from .services.location_search import search_locations
        use_location_groups = should_use_location_groups()
    except ImportError:
        use_location_groups = False
        search_locations = None
    
    # Get query parameters
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    per_page = int(request.GET.get('per_page', '25'))
    page = int(request.GET.get('page', '1'))
    
    context = {
        'query': query,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'page': page,
        'component_count': 0,
        'page_obj': None,
        'company_links': [],
        'error': None,
        'api_time': 0,
        'from_cache': False,
    }
    
    if not query:
        # No query, return empty context
        return render(request, 'checker/search_results_with_map_real.html', context)
    
    start_time = time.time()
    
    # Use location search if available
    if use_location_groups and search_locations:
        try:
            # Use the location search service
            result = search_locations(
                query=query,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            if result and 'location_groups' in result:
                # Create paginator from results
                paginator = Paginator(result['location_groups'], per_page)
                page_obj = paginator.get_page(page)
                
                context.update({
                    'page_obj': page_obj,
                    'component_count': result.get('total_components', 0),
                    'location_count': result.get('total_locations', 0),
                    'api_time': time.time() - start_time,
                })
            else:
                context['error'] = 'No results found'
                
        except Exception as e:
            context['error'] = f'Search error: {str(e)}'
    else:
        # Fallback to component search service
        from .services.component_search import search_components_service
        
        # We need to prevent the redirect that component_search does for small result sets
        # Add a suppress_map parameter
        request.GET = request.GET.copy()
        request.GET['suppress_map'] = 'true'
        
        # Call the service with our template
        try:
            # Import render_to_response to handle the response
            from django.http import HttpResponse
            
            # Call search_components_service
            response = search_components_service(request)
            
            # If it's a render response, we need to extract the context
            if hasattr(response, 'context_data'):
                # This is a TemplateResponse
                context.update(response.context_data)
            elif isinstance(response, HttpResponse) and hasattr(response, '_container'):
                # This is a regular HttpResponse from render()
                # We can't easily extract context, so we'll call the service differently
                # For now, just use basic context
                pass
                
        except Exception as e:
            context['error'] = f'Search error: {str(e)}'
    
    context['api_time'] = time.time() - start_time
    
    # Use the search_results_with_map template
    return render(request, 'checker/search_results_with_map_real.html', context)

@map_access_required
def search_results_with_map_google(request):
    """Search results with Google Maps using REAL search data - LocationGroups only"""
    import time
    from django.core.paginator import Paginator
    from django.conf import settings
    
    # First, check if we should use location groups
    try:
        from .services.location_group_check import should_use_location_groups
        from .services.location_search import search_locations
        use_location_groups = should_use_location_groups()
    except ImportError:
        use_location_groups = False
        search_locations = None
    
    # Get query parameters
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    per_page = int(request.GET.get('per_page', '25'))
    page = int(request.GET.get('page', '1'))
    
    context = {
        'query': query,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'page': page,
        'component_count': 0,
        'page_obj': None,
        'company_links': [],
        'error': None,
        'api_time': 0,
        'from_cache': False,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    
    if not query:
        # No query, return empty context
        return render(request, 'checker/search_results_with_map_google.html', context)
    
    start_time = time.time()
    
    # Use location search if available
    if use_location_groups and search_locations:
        try:
            # Use the location search service
            result = search_locations(
                query=query,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            if result and 'location_groups' in result:
                # Create paginator from results
                paginator = Paginator(result['location_groups'], per_page)
                page_obj = paginator.get_page(page)
                
                context.update({
                    'page_obj': page_obj,
                    'component_count': result.get('total_components', 0),
                    'location_count': result.get('total_locations', 0),
                    'api_time': time.time() - start_time,
                })
            else:
                context['error'] = 'No results found'
                
        except Exception as e:
            context['error'] = f'Search error: {str(e)}'
    else:
        # Fallback to component search service
        from .services.component_search import search_components_service
        
        # We need to prevent the redirect that component_search does for small result sets
        # Add a suppress_map parameter
        request.GET = request.GET.copy()
        request.GET['suppress_map'] = 'true'
        
        # Call the service with our template
        try:
            # Import render_to_response to handle the response
            from django.http import HttpResponse
            
            # Call search_components_service
            response = search_components_service(request)
            
            # If it's a render response, we need to extract the context
            if hasattr(response, 'context_data'):
                # This is a TemplateResponse
                context.update(response.context_data)
            elif isinstance(response, HttpResponse) and hasattr(response, '_container'):
                # This is a regular HttpResponse from render()
                # We can't easily extract context, so we'll call the service differently
                # For now, just use basic context
                pass
                
        except Exception as e:
            context['error'] = f'Search error: {str(e)}'
    
    context['api_time'] = time.time() - start_time
    
    # Use the Google Maps template
    return render(request, 'checker/search_results_with_map_google.html', context)