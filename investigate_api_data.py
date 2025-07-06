import requests
from collections import Counter, defaultdict

def investigate_api_discrepancies():
    """Deep dive into API data to understand the counting issues"""
    
    print("🔍 INVESTIGATING API DATA QUALITY")
    print("="*50)
    
    # 1. First verify the total count claim
    component_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
    component_resource_id = '790f5fa0-f8eb-4d82-b98d-0d34d3e404e8'
    
    # Get total count
    params = {'resource_id': component_resource_id, 'limit': 0}
    response = requests.get(component_api_url, params=params, timeout=30)
    data = response.json()
    
    if data.get('success'):
        total_claimed = data.get('result', {}).get('total', 0)
        print(f"API claims total components: {total_claimed:,}")
    
    # 2. Sample recent records to check for duplicates
    print("\n📊 SAMPLING RECENT RECORDS FOR DUPLICATES")
    
    params = {'resource_id': component_resource_id, 'limit': 1000, 'sort': '_id desc'}
    response = requests.get(component_api_url, params=params, timeout=30)
    data = response.json()
    
    if data.get('success'):
        records = data.get('result', {}).get('records', [])
        
        # Check for duplicate component IDs
        component_ids = [r.get('Component ID') for r in records if r.get('Component ID')]
        cmu_ids = [r.get('CMU ID') for r in records if r.get('CMU ID')]
        
        print(f"Sample of {len(records)} records:")
        print(f"  Unique Component IDs: {len(set(component_ids))}/{len(component_ids)}")
        print(f"  Unique CMU IDs: {len(set(cmu_ids))}/{len(cmu_ids)}")
        
        # Look for obvious duplicates
        comp_id_counts = Counter(component_ids)
        cmu_id_counts = Counter(cmu_ids)
        
        duplicates = [comp_id for comp_id, count in comp_id_counts.items() if count > 1]
        if duplicates:
            print(f"  🚨 Found {len(duplicates)} duplicate Component IDs in sample")
            for dup in duplicates[:5]:
                print(f"    {dup}: {comp_id_counts[dup]} times")
        
    # 3. Check specific Octopus CMU to understand the inflation
    print("\n🐙 DETAILED OCTOPUS CMU ANALYSIS")
    
    # Check one of the large CMUs in detail
    large_cmu = 'OCTO27'
    params = {
        'resource_id': component_resource_id,
        'q': f'"{large_cmu}"',
        'limit': 50  # Get actual records, not just count
    }
    
    response = requests.get(component_api_url, params=params, timeout=30)
    data = response.json()
    
    if data.get('success'):
        records = data.get('result', {}).get('records', [])
        total_for_cmu = data.get('result', {}).get('total', 0)
        
        print(f"CMU {large_cmu}: Claims {total_for_cmu:,} components")
        print(f"Sample of first {len(records)} records:")
        
        # Analyze the actual records
        locations = []
        descriptions = []
        capacities = []
        years = []
        
        for i, record in enumerate(records[:10]):
            comp_id = record.get('Component ID', 'Unknown')
            location = record.get('Location and Post Code', 'No location')
            description = record.get('Description of CMU Components', 'No description')
            capacity = record.get('De-Rated Capacity', 'Unknown')
            year = record.get('Delivery Year', 'Unknown')
            
            print(f"  {i+1}. {comp_id} | {capacity} MW | {year} | {location[:50]}")
            
            locations.append(location)
            descriptions.append(description)
            capacities.append(capacity)
            years.append(year)
        
        # Check for patterns that suggest aggregation
        unique_locations = len(set(locations))
        unique_descriptions = len(set(descriptions))
        unique_capacities = len(set(capacities))
        
        print(f"\nPatterns in sample:")
        print(f"  Unique locations: {unique_locations}/{len(records)}")
        print(f"  Unique descriptions: {unique_descriptions}/{len(records)}")
        print(f"  Unique capacities: {unique_capacities}/{len(records)}")
        
        if unique_locations < len(records) / 2:
            print("  🚨 HIGH DUPLICATION - Same locations repeated")
        
    # 4. Compare with your database for same CMU
    print(f"\n💾 CHECKING YOUR DATABASE FOR {large_cmu}")
    
    try:
        import os
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
        django.setup()
        
        from checker.models import Component
        
        db_components = Component.objects.filter(cmu_id=large_cmu)
        db_count = db_components.count()
        
        print(f"Your database has {db_count} components for {large_cmu}")
        
        if db_count > 0:
            print("Sample from your database:")
            for i, comp in enumerate(db_components[:5]):
                print(f"  {i+1}. {comp.component_id} | {comp.location[:50] if comp.location else 'No location'}")
        
    except Exception as e:
        print(f"Could not check database: {e}")
    
    # 5. Check if the issue is pagination/API behavior
    print(f"\n🔄 TESTING API PAGINATION BEHAVIOR")
    
    # Try getting different pages of the same CMU search
    for page_offset in [0, 1000, 2000]:
        params = {
            'resource_id': component_resource_id,
            'q': f'"{large_cmu}"',
            'limit': 100,
            'offset': page_offset
        }
        
        response = requests.get(component_api_url, params=params, timeout=30)
        data = response.json()
        
        if data.get('success'):
            records = data.get('result', {}).get('records', [])
            if records:
                first_comp = records[0].get('Component ID', 'Unknown')
                last_comp = records[-1].get('Component ID', 'Unknown') 
                print(f"  Offset {page_offset}: {len(records)} records, first={first_comp}, last={last_comp}")
            else:
                print(f"  Offset {page_offset}: No records returned")
                break

if __name__ == "__main__":
    investigate_api_discrepancies()