"""
Optimized component search service that passes LocationGroup objects directly to templates
"""
import logging
import time
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q

from ..models import LocationGroup, Component
# Remove unused import - we'll query LocationGroup directly
from .postcode_helpers import get_all_postcodes_for_area

logger = logging.getLogger(__name__)


def search_components_optimized(request):
    """
    Optimized search that passes LocationGroup objects directly to template
    without converting to dictionaries
    """
    start_time = time.time()
    
    # Get search parameters
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    sort_by = request.GET.get('sort_by', 'relevance')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Initialize timing
    timings = {}
    
    # Search for companies (still useful for the sidebar)
    company_search_start = time.time()
    company_links = []
    
    if query:
        # Get matching companies from LocationGroups
        from ..models import CompanyLinks
        from ..utils import normalize
        
        # Find companies that match the query
        matching_companies = set()
        
        # Search in CompanyLinks for exact matches
        company_matches = CompanyLinks.objects.filter(
            company_name__icontains=query
        ).order_by('-component_count')[:10]
        
        for company_link in company_matches:
            company_id = normalize(company_link.company_name)
            html = f'<a href="/company-optimized/{company_id}/">{company_link.company_name}</a> <span class="text-muted">({company_link.component_count} components)</span>'
            company_links.append({
                'name': company_link.company_name,
                'count': company_link.component_count,
                'html': html
            })
    
    timings['company_search'] = time.time() - company_search_start
    
    # Use LocationGroup search
    location_search_start = time.time()
    
    if query:
        # Handle multi-word queries by splitting and requiring ALL words to match
        query_parts = query.split()
        
        # First, try to search directly in LocationGroup
        if len(query_parts) > 1:
            # Multi-word search: each word must match somewhere
            location_filter = Q()
            for part in query_parts:
                part_filter = (
                    Q(location__icontains=part) |
                    Q(companies__icontains=part) |
                    Q(descriptions__icontains=part) |
                    Q(cmu_ids__icontains=part) |
                    Q(technologies__icontains=part)
                )
                location_filter &= part_filter  # AND logic - all parts must match
            
            logger.info(f"Multi-word search '{query}': split into {len(query_parts)} parts")
        else:
            # Single word search - use OR logic across all fields
            location_filter = (
                Q(location__icontains=query) |
                Q(companies__icontains=query) |
                Q(descriptions__icontains=query) |
                Q(cmu_ids__icontains=query) |
                Q(technologies__icontains=query)
            )
        
        # Get LocationGroups that match
        location_groups = LocationGroup.objects.filter(location_filter)
        
        # Check for postcodes as fallback
        if not location_groups.exists():
            postcodes = get_all_postcodes_for_area(query)
            if postcodes:
                # Fall back to component search for postcodes
                postcode_filters = Q()
                for postcode in postcodes:
                    postcode_filters |= Q(outward_code=postcode)
                
                matching_locations = Component.objects.filter(
                    postcode_filters
                ).values_list('location', flat=True).distinct()
                
                location_groups = LocationGroup.objects.filter(location__in=matching_locations)
        
        logger.info(f"Search '{query}': found {location_groups.count()} matching LocationGroups")
    else:
        # No query - get all LocationGroups
        location_groups = LocationGroup.objects.all()
    
    # Apply sorting
    if sort_by == 'location':
        order_field = 'location'
    elif sort_by == 'capacity':
        order_field = 'normalized_capacity_mw'
    elif sort_by == 'components':
        order_field = 'component_count'
    else:
        # Default to location for now (could add relevance ranking later)
        order_field = 'location'
    
    if sort_order == 'desc' and order_field != 'location':
        order_field = f'-{order_field}'
    
    location_groups = location_groups.order_by(order_field)
    
    timings['location_search'] = time.time() - location_search_start
    
    # Paginate the LocationGroup queryset directly
    pagination_start = time.time()
    paginator = Paginator(location_groups, per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    timings['pagination'] = time.time() - pagination_start
    
    # Calculate total component count more efficiently using aggregation
    from django.db.models import Sum
    total_components = location_groups.aggregate(total=Sum('component_count'))['total'] or 0
    
    # Build context
    context = {
        'query': query,
        'page_obj': page_obj,
        'company_links': company_links,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'per_page': per_page,
        'total_components': total_components,
        'total_locations': paginator.count,  # Total number of unique locations
        'locations_on_page': len(page_obj.object_list),  # Locations on current page
        'api_time': time.time() - start_time,
        'timings': timings,
        'page': page,  # Current page number
    }
    
    # Log performance
    logger.info(f"Optimized search for '{query}' completed in {context['api_time']:.2f}s")
    logger.info(f"Timings: {timings}")
    
    # Use the optimized template
    return render(request, 'checker/search_locationgroup_optimized.html', context)