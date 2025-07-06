#!/usr/bin/env python
import os
import sys
import django
from collections import defaultdict

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Count, Sum, Avg, Min, Max
import json

def build_imperial_college_context():
    """Build the context data for Imperial College location detail page"""
    
    location_name = "Imperial College London"
    
    # Get all components at this location
    components = Component.objects.filter(
        location__icontains="Imperial College"
    ).order_by('description', 'cmu_id', 'delivery_year')
    
    # Build asset structure
    assets_dict = defaultdict(lambda: {
        'description': '',
        'primary_technology': '',
        'primary_company': '',
        'cmus': defaultdict(lambda: {
            'auctions': [],
            'total_records': 0,
            'records_with_capacity': 0,
            'avg_capacity': 0,
            'has_duplicates': False
        })
    })
    
    # Track duplicates
    seen_combinations = set()
    duplicate_count = 0
    missing_capacity_count = 0
    
    for comp in components:
        desc = comp.description or 'No Description'
        cmu_id = comp.cmu_id or 'No CMU'
        
        # Set asset info
        if desc not in assets_dict:
            assets_dict[desc]['description'] = desc
            assets_dict[desc]['primary_technology'] = comp.technology or 'Unknown'
            assets_dict[desc]['primary_company'] = comp.company_name or 'Unknown'
        
        # Check for duplicates
        combo_key = (desc, cmu_id, comp.auction_name, comp.delivery_year)
        is_duplicate = combo_key in seen_combinations
        if is_duplicate:
            duplicate_count += 1
        seen_combinations.add(combo_key)
        
        # Track missing capacity
        if not comp.derated_capacity_mw:
            missing_capacity_count += 1
        
        # Add auction data
        auction_data = {
            'component_id': comp.id,
            'auction_name': comp.auction_name,
            'delivery_year': comp.delivery_year,
            'derated_mw': comp.derated_capacity_mw,
            'cmu_registry_mw': None,  # Would come from CMU registry
            'is_duplicate': is_duplicate
        }
        
        assets_dict[desc]['cmus'][cmu_id]['auctions'].append(auction_data)
        assets_dict[desc]['cmus'][cmu_id]['total_records'] += 1
        if comp.derated_capacity_mw:
            assets_dict[desc]['cmus'][cmu_id]['records_with_capacity'] += 1
    
    # Calculate averages and detect duplicates within CMUs
    for asset_data in assets_dict.values():
        for cmu_id, cmu_data in asset_data['cmus'].items():
            # Calculate average capacity
            capacities = [a['derated_mw'] for a in cmu_data['auctions'] if a['derated_mw']]
            if capacities:
                cmu_data['avg_capacity'] = sum(capacities) / len(capacities)
            
            # Check for duplicates (same auction year appearing multiple times)
            auction_years = [a['delivery_year'] for a in cmu_data['auctions']]
            if len(auction_years) != len(set(auction_years)):
                cmu_data['has_duplicates'] = True
    
    # Convert to list for template
    assets = []
    for desc, asset_data in assets_dict.items():
        asset = {
            'description': asset_data['description'],
            'primary_technology': asset_data['primary_technology'],
            'primary_company': asset_data['primary_company'],
            'cmus': dict(asset_data['cmus'])
        }
        assets.append(asset)
    
    # Calculate totals
    total_components = components.count()
    total_assets = len(assets)
    total_capacity = components.aggregate(Sum('derated_capacity_mw'))['derated_capacity_mw__sum'] or 0
    
    # Get year range
    year_range = components.aggregate(
        min_year=Min('delivery_year'),
        max_year=Max('delivery_year')
    )
    year_str = f"{year_range['min_year']} - {year_range['max_year']}"
    
    context = {
        'location_name': location_name,
        'total_assets': total_assets,
        'total_components': total_components,
        'total_capacity_mw': total_capacity,
        'year_range': year_str,
        'assets': assets,
        'duplicate_count': duplicate_count,
        'missing_capacity_count': missing_capacity_count,
        'capacity_mismatch_count': 0,  # Would need CMU registry data
        'has_coordinates': False  # Would check if location has lat/lng
    }
    
    return context

def print_context_summary(context):
    """Print a summary of the context data"""
    print("\nIMPERIAL COLLEGE LOCATION DETAIL - CONTEXT SUMMARY")
    print("=" * 80)
    print(f"Location: {context['location_name']}")
    print(f"Total Assets (unique descriptions): {context['total_assets']}")
    print(f"Total Component Records: {context['total_components']}")
    print(f"Total Capacity: {context['total_capacity_mw']:.2f} MW")
    print(f"Year Range: {context['year_range']}")
    print(f"\nData Quality Issues:")
    print(f"  - Duplicate records: {context['duplicate_count']}")
    print(f"  - Missing capacity data: {context['missing_capacity_count']}")
    
    print("\nAsset Breakdown:")
    for i, asset in enumerate(context['assets'], 1):
        print(f"\n{i}. {asset['description']}")
        print(f"   Technology: {asset['primary_technology']}")
        print(f"   Company: {asset['primary_company']}")
        
        for cmu_id, cmu_data in asset['cmus'].items():
            print(f"\n   CMU: {cmu_id}")
            print(f"     Total records: {cmu_data['total_records']}")
            print(f"     Records with capacity: {cmu_data['records_with_capacity']}")
            print(f"     Average capacity: {cmu_data['avg_capacity']:.2f} MW")
            if cmu_data['has_duplicates']:
                print(f"     ⚠️  Has duplicate auction years")
            
            # Show first few auctions
            print(f"     Auctions:")
            for auction in cmu_data['auctions'][:3]:
                capacity_str = f"{auction['derated_mw']:.2f} MW" if auction['derated_mw'] else "No capacity"
                dup_str = " [DUPLICATE]" if auction['is_duplicate'] else ""
                print(f"       - {auction['delivery_year']}: {capacity_str}{dup_str}")
            if len(cmu_data['auctions']) > 3:
                print(f"       ... and {len(cmu_data['auctions']) - 3} more")

def save_html_preview(context):
    """Save a preview of how the page would look"""
    from django.template.loader import render_to_string
    from django.http import HttpRequest
    
    # Create a mock request
    request = HttpRequest()
    request.method = 'GET'
    
    try:
        # Try to render with the template
        html = render_to_string('checker/location_detail_prototype.html', context, request)
        
        with open('imperial_college_preview.html', 'w') as f:
            f.write(html)
        print("\nHTML preview saved to: imperial_college_preview.html")
    except Exception as e:
        print(f"\nCouldn't render full template: {e}")
        print("Context data saved to: imperial_college_context.json")
        
        with open('imperial_college_context.json', 'w') as f:
            # Convert to JSON-serializable format
            json_context = {
                k: v for k, v in context.items()
                if k != 'assets'  # Handle assets separately due to complex structure
            }
            json_context['assets'] = []
            for asset in context['assets']:
                json_asset = {
                    'description': asset['description'],
                    'primary_technology': asset['primary_technology'],
                    'primary_company': asset['primary_company'],
                    'cmus': {}
                }
                for cmu_id, cmu_data in asset['cmus'].items():
                    json_asset['cmus'][cmu_id] = {
                        'total_records': cmu_data['total_records'],
                        'records_with_capacity': cmu_data['records_with_capacity'],
                        'avg_capacity': float(cmu_data['avg_capacity']),
                        'has_duplicates': cmu_data['has_duplicates'],
                        'auction_count': len(cmu_data['auctions'])
                    }
                json_context['assets'].append(json_asset)
            
            json.dump(json_context, f, indent=2)

if __name__ == "__main__":
    context = build_imperial_college_context()
    print_context_summary(context)
    save_html_preview(context)