import requests
from collections import Counter

component_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
component_resource_id = '790f5fa0-f8eb-4d82-b98d-0d34d3e404e8'

params = {
    'resource_id': component_resource_id,
    'limit': 1000,
    'sort': '_id desc'
}

try:
    response = requests.get(component_api_url, params=params, timeout=30)
    data = response.json()
    
    if data.get('success'):
        records = data.get('result', {}).get('records', [])
        
        print(f'Analyzing {len(records)} records...')
        
        # Check first record fields
        if records:
            print('\nSample record fields containing company/name:')
            for key, value in records[0].items():
                if any(word in key.lower() for word in ['company', 'name', 'applicant']):
                    print(f'  {key}: {str(value)[:100]}')
        
        # Find companies - checking multiple possible field names
        companies = []
        
        for record in records:
            # Try different field names that might contain company info
            company = (record.get('Company Name') or 
                      record.get('Applicant') or 
                      record.get('Name of Applicant') or
                      record.get('Company') or
                      None)
            
            if company and company != 'Unknown':
                companies.append(company)
        
        if companies:
            print('\n=== TOP COMPANIES IN LATEST 1000 RECORDS ===')
            company_counts = Counter(companies)
            for company, count in company_counts.most_common(15):
                print(f'{company}: {count}')
        else:
            print('\nNo company data found. Checking all field names...')
            if records:
                print('All fields in first record:')
                for key, value in records[0].items():
                    print(f'  {key}: {str(value)[:50]}')
                    
        # Now specifically search for ENEL X, Octopus, etc.
        print('\n=== SEARCHING FOR SPECIFIC COMPANIES ===')
        search_terms = ['ENEL X', 'ENEL', 'OCTOPUS', 'AXLE', 'Flexitricity']
        
        for term in search_terms:
            params_search = {
                'resource_id': component_resource_id,
                'q': term,
                'limit': 0
            }
            
            resp = requests.get(component_api_url, params=params_search, timeout=30)
            search_data = resp.json()
            
            if search_data.get('success'):
                total = search_data.get('result', {}).get('total', 0)
                print(f'{term}: {total:,} components')
        
except Exception as e:
    print(f'Error: {e}')