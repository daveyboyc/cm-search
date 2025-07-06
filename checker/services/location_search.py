"""
Location-based search using the LocationGroup model for efficient pagination.
This replaces the inefficient component fetching + grouping approach.
"""
import time
import logging
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, F
from django.core.cache import cache

from ..models import LocationGroup, Component
from .company_search import get_cmu_dataframe

logger = logging.getLogger(__name__)

# Import fast postcode helpers
try:
    from .postcode_helpers_fast import get_all_postcodes_for_area
    logger.info("Using FAST postcode helpers in location_search")
except ImportError:
    from .postcode_helpers import get_all_postcodes_for_area
    logger.warning("Using SLOW postcode helpers in location_search")


def search_locations(query, page=1, per_page=10, sort_by='relevance', sort_order='desc'):
    """
    Search for locations using the LocationGroup model.
    Returns paginated LocationGroup objects instead of components.
    """
    start_time = time.time()
    debug_info = {
        'query': query,
        'page': page,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_order': sort_order,
    }
    
    if not query:
        # No query - return all locations
        queryset = LocationGroup.objects.all()
    else:
        # First, find all locations that have matching components
        # Search across multiple fields like the original search does
        component_filter = (
            Q(location__icontains=query) |
            Q(company_name__icontains=query) |
            Q(description__icontains=query) |
            Q(cmu_id__icontains=query) |
            Q(technology__icontains=query)
        )
        
        # Check if it's a postcode-based search
        postcodes = get_all_postcodes_for_area(query)
        if postcodes:
            postcode_filters = Q()
            for postcode in postcodes:
                postcode_filters |= Q(outward_code=postcode)
            component_filter |= postcode_filters
            debug_info['search_type'] = 'mixed'
            debug_info['postcodes_found'] = len(postcodes)
        else:
            debug_info['search_type'] = 'text'
        
        # Find unique locations that have matching components
        matching_locations = Component.objects.filter(
            component_filter
        ).values_list('location', flat=True).distinct()
        
        # Now get the LocationGroups for these locations
        queryset = LocationGroup.objects.filter(location__in=matching_locations)
    
    # Apply sorting
    if sort_by == 'capacity':
        order_field = 'normalized_capacity_mw'
    elif sort_by == 'components':
        order_field = 'component_count'
    else:  # relevance or location
        order_field = 'location'
    
    if sort_order == 'desc':
        order_field = f'-{order_field}'
    
    queryset = queryset.order_by(order_field)
    
    # Get total count before pagination
    total_count = queryset.count()
    debug_info['total_locations'] = total_count
    
    # Paginate
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    
    # Calculate total component count across ALL matching locations (not just this page)
    total_components = queryset.aggregate(total=models.Sum('component_count'))['total'] or 0
    
    # Components on just this page
    page_components = sum(lg.component_count for lg in page_obj.object_list)
    
    debug_info['locations_on_page'] = len(page_obj.object_list)
    debug_info['components_on_page'] = page_components
    debug_info['total_components_all_pages'] = total_components
    debug_info['query_time'] = time.time() - start_time
    
    return {
        'page_obj': page_obj,
        'location_groups': page_obj.object_list,
        'total_locations': total_count,
        'total_components': total_components,
        'debug_info': debug_info,
        'query': query,
        'sort_by': sort_by,
        'sort_order': sort_order,
    }


def get_location_components(location, description=None, cmu_id=None, auction_year=None):
    """
    Get all components for a specific location with optional filtering.
    Used by the location detail view.
    """
    # Start with all components at this location
    components = Component.objects.filter(location=location)
    
    # Apply additional filters if provided
    if description:
        components = components.filter(description=description)
    
    if cmu_id:
        components = components.filter(cmu_id=cmu_id)
    
    if auction_year:
        components = components.filter(auction_name__icontains=auction_year)
    
    # Order by delivery year descending, then by description
    components = components.order_by('-delivery_year', 'description')
    
    return components


def prepare_location_display_data(location_group):
    """
    Prepare display data for a LocationGroup.
    Organizes components by description, CMU, and auction year.
    """
    # Get all components for this location
    components = Component.objects.filter(location=location_group.location).order_by(
        'description', 'cmu_id', '-delivery_year'
    )
    
    # Organize by description -> CMU -> Auction
    organized_data = {}
    
    for component in components:
        desc = component.description or "No description"
        cmu = component.cmu_id
        auction = component.auction_name or "Unknown auction"
        
        if desc not in organized_data:
            organized_data[desc] = {}
        
        if cmu not in organized_data[desc]:
            organized_data[desc][cmu] = {
                'cmu_id': cmu,
                'auctions': {},
                'company': component.company_name,
                'technology': component.technology,
            }
        
        if auction not in organized_data[desc][cmu]['auctions']:
            organized_data[desc][cmu]['auctions'][auction] = []
        
        organized_data[desc][cmu]['auctions'][auction].append(component)
    
    return organized_data


def check_cmu_aggregation(location_group):
    """
    Check if this location is part of an aggregated CMU.
    Returns information about the aggregation if found.
    """
    # Get a sample component from this location
    sample_component = Component.objects.filter(location=location_group.location).first()
    if not sample_component:
        return None
    
    # Count how many locations this CMU spans
    cmu_locations = Component.objects.filter(
        cmu_id=sample_component.cmu_id
    ).values('location').distinct().count()
    
    if cmu_locations > 1:
        # This is part of an aggregated CMU
        # Get the CMU data to find total capacity
        cmu_df, _ = get_cmu_dataframe()
        if cmu_df is not None and not cmu_df.empty:
            # Find the CMU data by filtering
            cmu_data = cmu_df[cmu_df["CMU ID"] == sample_component.cmu_id]
            if not cmu_data.empty:
                cmu_row = cmu_data.iloc[0]
                total_capacity = cmu_row.get('De-rated Capacity (MW)', 0)
                
                return {
                    'is_aggregated': True,
                    'cmu_id': sample_component.cmu_id,
                    'total_locations': cmu_locations,
                    'total_capacity': total_capacity,
                    'applicant': cmu_row.get('Name of Applicant', 'Unknown'),
                }
    
    return {'is_aggregated': False}