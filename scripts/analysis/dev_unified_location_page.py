#!/usr/bin/env python
"""
Create a prototype unified location page for Imperial College
Shows all components grouped by description/CMU with links
"""
import os
import sys
import django
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.urls import reverse

def build_imperial_college_data():
    """Build the data structure for Imperial College unified page"""
    
    location_name = "Imperial College London"
    
    # Get all components at this location
    components = Component.objects.filter(
        location__icontains="Imperial College"
    ).order_by('description', 'cmu_id', 'delivery_year')
    
    # Build the grouped structure
    location_data = {
        'location_name': location_name,
        'total_components': components.count(),
        'assets': defaultdict(lambda: {
            'description': '',
            'technology': '',
            'company': '',
            'cmus': defaultdict(lambda: {
                'auctions': []
            })
        })
    }
    
    # Track unique CMU IDs for CMU links
    unique_cmu_ids = set()
    
    for comp in components:
        desc = comp.description or 'No Description'
        cmu_id = comp.cmu_id or 'No CMU'
        
        # Track unique CMUs
        if cmu_id != 'No CMU':
            unique_cmu_ids.add(cmu_id)
        
        # Set asset info
        if desc not in location_data['assets']:
            location_data['assets'][desc]['description'] = desc
            location_data['assets'][desc]['technology'] = comp.technology or 'Unknown'
            location_data['assets'][desc]['company'] = comp.company_name or 'Unknown'
        
        # Build the component link (this is what we're moving from search results)
        component_link = f"/component/{comp.id}/"  # Would use reverse() in real code
        
        # Add auction data with link
        auction_data = {
            'component_id': comp.id,
            'auction_name': comp.auction_name,
            'delivery_year': comp.delivery_year,
            'derated_mw': comp.derated_capacity_mw,
            'component_link': component_link,
            'cmu_id': cmu_id
        }
        
        location_data['assets'][desc]['cmus'][cmu_id]['auctions'].append(auction_data)
    
    # Build CMU links (expensive operation, but only done once here)
    location_data['cmu_links'] = {}
    for cmu_id in unique_cmu_ids:
        # In real implementation, this would be the expensive CMU link building
        location_data['cmu_links'][cmu_id] = f"/cmu/{cmu_id}/"
    
    return location_data

def generate_html_prototype(data):
    """Generate HTML prototype for the unified location page"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{data['location_name']} - Unified Location View</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .asset-card {{ margin-bottom: 20px; }}
        .auction-row:hover {{ background-color: #f8f9fa; }}
        .cmu-section {{ margin-bottom: 15px; }}
    </style>
</head>
<body>
    <div class="container mt-4">
        <h1>{data['location_name']}</h1>
        <p class="text-muted">Unified view of {data['total_components']} component records at this location</p>
        
        <!-- Performance Note -->
        <div class="alert alert-info">
            <strong>Performance Note:</strong> Link building now happens here (once) instead of in search results (100x).
            This page replaces {data['total_components']} individual component detail pages.
        </div>
        
        <!-- CMU Quick Links -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>CMU IDs at this Location</h5>
            </div>
            <div class="card-body">
                {"".join(f'<a href="{link}" class="btn btn-sm btn-outline-primary me-2">{cmu_id}</a>' 
                         for cmu_id, link in data['cmu_links'].items())}
            </div>
        </div>
"""
    
    # Generate asset sections
    for desc, asset_data in data['assets'].items():
        html += f"""
        <!-- Asset: {desc[:60]}... -->
        <div class="card asset-card">
            <div class="card-header">
                <h5>{desc}</h5>
                <small class="text-muted">
                    Technology: {asset_data['technology']} | 
                    Company: {asset_data['company']}
                </small>
            </div>
            <div class="card-body">
"""
        
        # Generate CMU sections within each asset
        for cmu_id, cmu_data in asset_data['cmus'].items():
            cmu_link = data['cmu_links'].get(cmu_id, '#')
            html += f"""
                <div class="cmu-section">
                    <h6>
                        CMU: <a href="{cmu_link}">{cmu_id}</a>
                        <small class="text-muted">({len(cmu_data['auctions'])} auction records)</small>
                    </h6>
                    <table class="table table-sm table-hover">
                        <thead>
                            <tr>
                                <th>Auction</th>
                                <th>Delivery Year</th>
                                <th>Capacity (MW)</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
"""
            
            # Generate auction rows with component links
            for auction in sorted(cmu_data['auctions'], key=lambda x: x['delivery_year']):
                capacity_display = f"{auction['derated_mw']:.2f}" if auction['derated_mw'] else "Not specified"
                html += f"""
                            <tr class="auction-row">
                                <td>{auction['auction_name']}</td>
                                <td>{auction['delivery_year']}</td>
                                <td>{capacity_display}</td>
                                <td>
                                    <a href="{auction['component_link']}" 
                                       class="btn btn-sm btn-outline-secondary"
                                       title="View original component record #{auction['component_id']}">
                                        View Record
                                    </a>
                                    <button class="btn btn-sm btn-outline-info" 
                                            onclick="loadRawData({auction['component_id']})">
                                        Raw Data
                                    </button>
                                </td>
                            </tr>
"""
            
            html += """
                        </tbody>
                    </table>
                </div>
"""
        
        html += """
            </div>
        </div>
"""
    
    html += """
        <!-- Raw Data Modal (placeholder) -->
        <div class="modal fade" id="rawDataModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Component Raw Data</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="rawDataContent">
                        <!-- Raw data loaded here via AJAX -->
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        function loadRawData(componentId) {
            // In real implementation: fetch('/api/component/' + componentId + '/raw-data/')
            document.getElementById('rawDataContent').innerHTML = 
                '<p>Loading raw data for component #' + componentId + '...</p>' +
                '<pre>CMU Registry Data: ...</pre>' +
                '<pre>Component Additional Data: ...</pre>';
            new bootstrap.Modal(document.getElementById('rawDataModal')).show();
        }
        </script>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </div>
</body>
</html>
"""
    
    return html

def analyze_performance_impact():
    """Compare performance impact of old vs new approach"""
    
    print("\nPERFORMANCE IMPACT ANALYSIS")
    print("=" * 80)
    
    # Simulate battery search
    battery_components = Component.objects.filter(
        description__icontains='battery'
    ).count()
    
    battery_locations = Component.objects.filter(
        description__icontains='battery'
    ).values('location').distinct().count()
    
    print(f"\nBattery Search Example:")
    print(f"Total components: {battery_components}")
    print(f"Unique locations: {battery_locations}")
    
    print(f"\nOLD APPROACH (component-based search):")
    print(f"  - Search results show 100 components per page")
    print(f"  - Link building: 100 times per page")
    print(f"  - Total pages: {battery_components // 100}")
    
    print(f"\nNEW APPROACH (location-based search):")
    print(f"  - Search results show 10 locations per page")
    print(f"  - Link building: 10 times per page (in search)")
    print(f"  - Plus once per location detail page (when clicked)")
    print(f"  - Total pages: {battery_locations // 10}")
    
    print(f"\nPERFORMANCE GAIN:")
    print(f"  - Link building reduced by: {100/10:.0f}x in search results")
    print(f"  - Pagination improved by: {(battery_components/100) / (battery_locations/10):.1f}x")

if __name__ == "__main__":
    # Build the data
    data = build_imperial_college_data()
    
    # Generate HTML
    html = generate_html_prototype(data)
    
    # Save to file
    with open('imperial_college_unified.html', 'w') as f:
        f.write(html)
    
    print("Generated: imperial_college_unified.html")
    
    # Print summary
    print(f"\nImperial College Unified Page Summary:")
    print(f"Total components: {data['total_components']}")
    print(f"Unique assets: {len(data['assets'])}")
    print(f"Unique CMUs: {len(data['cmu_links'])}")
    
    # Show what this replaces
    print(f"\nThis single page replaces:")
    print(f"  - {data['total_components']} individual component detail pages")
    print(f"  - Link building moved from search results to here")
    
    # Analyze performance impact
    analyze_performance_impact()