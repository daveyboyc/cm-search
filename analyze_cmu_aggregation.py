import requests
from collections import defaultdict

def analyze_company_aggregation(company_name, max_cmus=50):
    """Analyze how many components per CMU for a specific company"""
    
    # First get CMUs for this company
    cmu_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
    cmu_resource_id = '25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6'
    
    print(f"\n=== ANALYZING {company_name.upper()} ===")
    
    # Get CMUs for this company
    cmu_params = {
        'resource_id': cmu_resource_id,
        'q': company_name,
        'limit': max_cmus
    }
    
    try:
        response = requests.get(cmu_api_url, params=cmu_params, timeout=30)
        data = response.json()
        
        if not data.get('success'):
            print(f"Failed to get CMU data for {company_name}")
            return
            
        cmus = data.get('result', {}).get('records', [])
        total_cmus = data.get('result', {}).get('total', 0)
        
        print(f"Total CMUs: {total_cmus}")
        print(f"Analyzing first {len(cmus)} CMUs...")
        
        # Now check components for each CMU
        component_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
        component_resource_id = '790f5fa0-f8eb-4d82-b98d-0d34d3e404e8'
        
        cmu_component_counts = []
        sample_locations = set()
        
        for i, cmu in enumerate(cmus[:10]):  # Check first 10 CMUs
            cmu_id = cmu.get('CMU ID')
            if not cmu_id:
                continue
                
            # Get components for this CMU
            comp_params = {
                'resource_id': component_resource_id,
                'q': f'"{cmu_id}"',  # Exact match
                'limit': 0  # Just count
            }
            
            comp_response = requests.get(component_api_url, params=comp_params, timeout=30)
            comp_data = comp_response.json()
            
            if comp_data.get('success'):
                component_count = comp_data.get('result', {}).get('total', 0)
                cmu_component_counts.append(component_count)
                
                # Get sample locations for this CMU
                if component_count > 0:
                    sample_params = {
                        'resource_id': component_resource_id,
                        'q': f'"{cmu_id}"',
                        'limit': 5
                    }
                    
                    sample_response = requests.get(component_api_url, params=sample_params, timeout=30)
                    sample_data = sample_response.json()
                    
                    if sample_data.get('success'):
                        sample_components = sample_data.get('result', {}).get('records', [])
                        for comp in sample_components:
                            location = comp.get('Location and Post Code')
                            if location and len(location) > 10:  # Has actual address
                                sample_locations.add(location[:50])
                
                print(f"  CMU {cmu_id}: {component_count} components")
                
                if i >= 9:  # Stop after 10 CMUs
                    break
        
        # Analysis
        if cmu_component_counts:
            avg_components = sum(cmu_component_counts) / len(cmu_component_counts)
            max_components = max(cmu_component_counts)
            min_components = min(cmu_component_counts)
            
            print(f"\nAggregation Analysis:")
            print(f"  Average components per CMU: {avg_components:.1f}")
            print(f"  Range: {min_components} - {max_components} components per CMU")
            print(f"  Estimated total components: {total_cmus} CMUs × {avg_components:.0f} = {total_cmus * avg_components:,.0f}")
            
            print(f"\nSample locations ({len(sample_locations)} found):")
            for location in list(sample_locations)[:5]:
                print(f"  - {location}...")
            
            if len(sample_locations) == 0:
                print("  - No specific locations found (likely aggregated/residential)")
            
            return {
                'total_cmus': total_cmus,
                'avg_components_per_cmu': avg_components,
                'estimated_total_components': total_cmus * avg_components,
                'has_specific_locations': len(sample_locations) > 0
            }
    
    except Exception as e:
        print(f"Error analyzing {company_name}: {e}")
        return None

# Analyze the major players
companies = ['ENEL X', 'OCTOPUS', 'AXLE', 'FLEXITRICITY']
results = {}

for company in companies:
    result = analyze_company_aggregation(company)
    if result:
        results[company] = result

print("\n" + "="*60)
print("SUMMARY: RESIDENTIAL DSR AGGREGATION PATTERNS")
print("="*60)

total_estimated = 0
for company, data in results.items():
    print(f"{company}:")
    print(f"  - {data['total_cmus']:,} CMUs")
    print(f"  - ~{data['estimated_total_components']:,.0f} estimated components")
    print(f"  - {'Has specific locations' if data['has_specific_locations'] else 'Aggregated/no locations'}")
    total_estimated += data['estimated_total_components']

print(f"\nTotal estimated residential components: {total_estimated:,.0f}")
print(f"Your current database: 51,493 total components")
print(f"Difference: {total_estimated - 51493:,.0f} missing residential components")