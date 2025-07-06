import requests
from collections import defaultdict

def get_all_components_for_company(company_name):
    """Get ALL CMUs for a company and check their component counts"""
    
    print(f"\n=== DEEP ANALYSIS: {company_name.upper()} ===")
    
    # Get ALL CMUs for this company (not just first 50)
    cmu_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
    cmu_resource_id = '25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6'
    
    all_cmus = []
    offset = 0
    batch_size = 100
    
    while True:
        cmu_params = {
            'resource_id': cmu_resource_id,
            'q': company_name,
            'limit': batch_size,
            'offset': offset
        }
        
        try:
            response = requests.get(cmu_api_url, params=cmu_params, timeout=30)
            data = response.json()
            
            if not data.get('success'):
                break
                
            batch_cmus = data.get('result', {}).get('records', [])
            if not batch_cmus:
                break
                
            all_cmus.extend(batch_cmus)
            offset += batch_size
            
            if len(batch_cmus) < batch_size:
                break
                
        except Exception as e:
            print(f"Error fetching CMUs: {e}")
            break
    
    print(f"Found {len(all_cmus)} total CMUs for {company_name}")
    
    # Now check component counts for ALL CMUs
    component_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
    component_resource_id = '790f5fa0-f8eb-4d82-b98d-0d34d3e404e8'
    
    cmu_component_data = []
    
    for i, cmu in enumerate(all_cmus):
        cmu_id = cmu.get('CMU ID')
        if not cmu_id:
            continue
            
        # Get component count for this CMU
        comp_params = {
            'resource_id': component_resource_id,
            'q': f'"{cmu_id}"',  # Exact match
            'limit': 0  # Just count
        }
        
        try:
            comp_response = requests.get(component_api_url, params=comp_params, timeout=30)
            comp_data = comp_response.json()
            
            if comp_data.get('success'):
                component_count = comp_data.get('result', {}).get('total', 0)
                cmu_component_data.append({
                    'cmu_id': cmu_id,
                    'component_count': component_count
                })
                
                if component_count > 1000:  # Flag large aggregations
                    print(f"  🚨 LARGE CMU: {cmu_id} = {component_count:,} components")
                elif component_count > 100:
                    print(f"  ⚠️  Medium CMU: {cmu_id} = {component_count:,} components")
                
                if (i + 1) % 50 == 0:
                    print(f"  Processed {i + 1}/{len(all_cmus)} CMUs...")
                    
        except Exception as e:
            print(f"Error checking {cmu_id}: {e}")
    
    # Analysis
    if cmu_component_data:
        total_components = sum(d['component_count'] for d in cmu_component_data)
        avg_components = total_components / len(cmu_component_data)
        
        # Sort by component count
        sorted_data = sorted(cmu_component_data, key=lambda x: x['component_count'], reverse=True)
        
        print(f"\n📊 {company_name.upper()} ANALYSIS:")
        print(f"  Total CMUs: {len(cmu_component_data):,}")
        print(f"  Total Components: {total_components:,}")
        print(f"  Average per CMU: {avg_components:.1f}")
        
        print(f"\n🔝 TOP 10 LARGEST CMUs:")
        for i, data in enumerate(sorted_data[:10]):
            print(f"  {i+1}. {data['cmu_id']}: {data['component_count']:,} components")
        
        print(f"\n📈 DISTRIBUTION:")
        large_cmus = [d for d in cmu_component_data if d['component_count'] > 1000]
        medium_cmus = [d for d in cmu_component_data if 100 < d['component_count'] <= 1000]
        small_cmus = [d for d in cmu_component_data if d['component_count'] <= 100]
        
        print(f"  Large (>1000): {len(large_cmus)} CMUs = {sum(d['component_count'] for d in large_cmus):,} components")
        print(f"  Medium (100-1000): {len(medium_cmus)} CMUs = {sum(d['component_count'] for d in medium_cmus):,} components")
        print(f"  Small (≤100): {len(small_cmus)} CMUs = {sum(d['component_count'] for d in small_cmus):,} components")
        
        return total_components
    
    return 0

# Check both companies in detail
octopus_total = get_all_components_for_company('OCTOPUS')
axle_total = get_all_components_for_company('AXLE')

print("\n" + "="*60)
print("🎯 RESIDENTIAL DSR COMPONENT TOTALS")
print("="*60)
print(f"OCTOPUS: {octopus_total:,} total components")
print(f"AXLE: {axle_total:,} total components")
print(f"COMBINED: {octopus_total + axle_total:,} components")
print(f"")
print(f"Your database: 51,493 components")
print(f"Missing residential: {(octopus_total + axle_total) - 51493:,} components")
print(f"Percentage of missing data that's residential: {((octopus_total + axle_total) / 627893) * 100:.1f}%")