"""
Location detail view - shows all components at a specific location.
This is where expensive operations like link building happen.
"""
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.conf import settings
from .models import LocationGroup, Component, CMURegistry
from .services.location_search import prepare_location_display_data, check_cmu_aggregation
from .structured_data import generate_location_structured_data
from collections import defaultdict


def location_detail(request, location_id):
    """Display all components at a specific location."""
    location_group = get_object_or_404(LocationGroup, id=location_id)
    
    # Get organized component data
    organized_data = prepare_location_display_data(location_group)
    
    # Check if this is part of an aggregated CMU
    aggregation_info = check_cmu_aggregation(location_group)
    
    # Fetch CMU Registry data for all CMUs at this location
    cmu_registry_data = {}
    
    # Handle both old list format and new dict format
    cmu_ids_to_process = []
    if isinstance(location_group.cmu_ids, dict) and 'sample' in location_group.cmu_ids:
        # New format: use the sample CMU IDs
        cmu_ids_to_process = location_group.cmu_ids['sample']
    elif isinstance(location_group.cmu_ids, list):
        # Old format: use all CMU IDs
        cmu_ids_to_process = location_group.cmu_ids
    
    for cmu_id in cmu_ids_to_process:
        registry_entry = CMURegistry.objects.filter(cmu_id=cmu_id).first()
        if registry_entry and isinstance(registry_entry.raw_data, dict):
            cmu_registry_data[cmu_id] = registry_entry.raw_data
    
    # Extract common secondary trading details (if consistent across CMUs)
    trading_contacts = defaultdict(set)
    for cmu_id, registry_data in cmu_registry_data.items():
        if registry_data.get("Secondary Trading Contact - Email"):
            trading_contacts['emails'].add(registry_data["Secondary Trading Contact - Email"])
        if registry_data.get("Secondary Trading Contact - Telephone"):
            trading_contacts['phones'].add(registry_data["Secondary Trading Contact - Telephone"])
    
    # Build auction links for each CMU at this location
    # This is the expensive operation that we've moved from search results
    for desc_data in organized_data.values():
        for cmu_id, cmu_data in desc_data.items():
            # Build auction links to individual component detail pages
            auction_links = []
            for auction_name, components in cmu_data['auctions'].items():
                # If only one component in this auction, link directly to it
                if len(components) == 1:
                    link = {
                        'name': auction_name,
                        'url': reverse('component_detail_hierarchical', kwargs={'location_id': location_id, 'pk': components[0].pk}),
                        'component_count': 1,
                        'is_single': True
                    }
                    auction_links.append(link)
                else:
                    # Multiple components in same auction - create links for each
                    for idx, component in enumerate(components):
                        link = {
                            'name': f"{auction_name} ({idx + 1}/{len(components)})",
                            'url': reverse('component_detail_hierarchical', kwargs={'location_id': location_id, 'pk': component.pk}),
                            'component_count': len(components),
                            'is_single': False
                        }
                        auction_links.append(link)
            
            # Sort auction links by year (newest first)
            auction_links.sort(key=lambda x: x['name'], reverse=True)
            cmu_data['auction_links'] = auction_links
            
            # Add CMU registry data to each CMU
            if cmu_id in cmu_registry_data:
                cmu_data['registry_data'] = cmu_registry_data[cmu_id]
                # Extract key capacity data
                cmu_data['registry_capacity'] = cmu_registry_data[cmu_id].get("De-Rated Capacity")
                cmu_data['connection_capacity'] = cmu_registry_data[cmu_id].get("Connection / DSR Capacity")
                cmu_data['parent_company'] = cmu_registry_data[cmu_id].get("Parent Company")
    
    context = {
        'location_group': location_group,
        'organized_data': organized_data,
        'aggregation_info': aggregation_info,
        'total_components': location_group.component_count,
        'primary_technology': location_group.get_primary_technology(),
        'primary_company': location_group.get_primary_company(),
        'capacity_display': location_group.get_display_capacity(),
        'trading_emails': list(trading_contacts['emails']),
        'trading_phones': list(trading_contacts['phones']),
        'cmu_registry_data': cmu_registry_data,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'structured_data': generate_location_structured_data(location_group, organized_data, request),
    }
    
    return render(request, 'checker/location_detail_styled.html', context)