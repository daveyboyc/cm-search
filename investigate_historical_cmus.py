import requests
import os
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component

def investigate_historical_cmus():
    """Investigate why historical CMUs are appearing as 'new'"""
    
    print("🔍 INVESTIGATING HISTORICAL CMU MYSTERY")
    print("="*50)
    
    # List of "new" CMUs that claim to be historical
    historical_cmus = [
        'COTPS2', 'COTPS3', 'COTPS4',  # EDF Energy 2018-19
        'D1_144', 'D2_144', 'D3_144',  # First Hydro 2018-19
        'WG1-14',  # EDF Energy 2018-19
        'CM_LJ6',  # LIMEJUMP 2016-17
        'DOCK_A',  # EQUIVALENCE 2017-18
        'DE0117'   # MWAT 2018-19
    ]
    
    # Check if these companies exist in your database
    print("🏢 CHECKING COMPANIES IN YOUR DATABASE:")
    
    companies_to_check = ['EDF Energy Limited', 'First Hydro Company', 'LIMEJUMP LTD', 'EQUIVALENCE ENERGY LIMITED']
    
    for company in companies_to_check:
        components = Component.objects.filter(company_name__icontains=company.split()[0])  # Partial match
        cmu_count = components.values('cmu_id').distinct().count()
        total_components = components.count()
        
        if total_components > 0:
            print(f"  {company}: {total_components} components, {cmu_count} CMUs")
            
            # Show some CMU IDs for this company
            sample_cmus = list(components.values_list('cmu_id', flat=True).distinct()[:5])
            print(f"    Sample CMUs: {sample_cmus}")
        else:
            print(f"  {company}: NOT FOUND in your database")
    
    # Check specific historical CMUs in detail
    print(f"\n🔍 DETAILED CHECK OF HISTORICAL CMUs:")
    
    cmu_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
    cmu_resource_id = '25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6'
    
    for cmu_id in historical_cmus[:5]:  # Check first 5
        print(f"\n--- CMU: {cmu_id} ---")
        
        # Check in your database
        your_components = Component.objects.filter(cmu_id=cmu_id)
        print(f"Your database: {your_components.count()} components")
        
        # Get details from API
        params = {
            'resource_id': cmu_resource_id,
            'q': f'"{cmu_id}"',
            'limit': 1
        }
        
        try:
            response = requests.get(cmu_api_url, params=params, timeout=30)
            data = response.json()
            
            if data.get('success'):
                records = data.get('result', {}).get('records', [])
                if records:
                    record = records[0]
                    company = record.get('Name of Applicant', 'Unknown')
                    auction = record.get('Auction Name', 'Unknown')
                    cmu_name = record.get('CM Unit Name', 'Unknown')
                    
                    print(f"API details:")
                    print(f"  Company: {company}")
                    print(f"  Auction: {auction}")
                    print(f"  CMU Name: {cmu_name}")
                    
                    # Check if this company exists under different name in your DB
                    if your_components.count() == 0:
                        # Try to find similar company names
                        company_words = company.split()
                        for word in company_words:
                            if len(word) > 3:  # Skip short words
                                similar = Component.objects.filter(company_name__icontains=word)
                                if similar.exists():
                                    similar_companies = list(similar.values_list('company_name', flat=True).distinct()[:3])
                                    print(f"  💡 Found similar companies in your DB: {similar_companies}")
                                    break
        
        except Exception as e:
            print(f"Error checking {cmu_id}: {e}")
    
    # Check when these CMUs were last updated in the API
    print(f"\n📅 CHECKING CMU REGISTRY UPDATE PATTERNS:")
    
    # Get recent CMU updates
    params = {
        'resource_id': cmu_resource_id,
        'limit': 100,
        'sort': '_id desc'
    }
    
    try:
        response = requests.get(cmu_api_url, params=params, timeout=30)
        data = response.json()
        
        if data.get('success'):
            records = data.get('result', {}).get('records', [])
            
            # Check if any of our "historical" CMUs appear in recent updates
            recent_cmu_ids = [r.get('CMU ID') for r in records]
            
            historical_in_recent = [cmu for cmu in historical_cmus if cmu in recent_cmu_ids]
            
            if historical_in_recent:
                print(f"🚨 FOUND HISTORICAL CMUs IN RECENT API UPDATES:")
                for cmu in historical_in_recent:
                    print(f"  {cmu} appears in recent API data")
                print(f"  This suggests these CMUs were recently MODIFIED or RE-ADDED to the API")
            else:
                print(f"Historical CMUs not found in recent API updates")
    
    except Exception as e:
        print(f"Error checking recent updates: {e}")
    
    # Final hypothesis
    print(f"\n🎯 LIKELY EXPLANATIONS:")
    print(f"1. CMUs were recently MODIFIED in NESO system (new component IDs)")
    print(f"2. Companies changed names (EDF restructuring, etc.)")
    print(f"3. CMUs were decomissioned and recommissioned")
    print(f"4. API data was recently corrected/updated")
    print(f"5. Your previous crawls missed these specific CMUs due to different search terms")

if __name__ == "__main__":
    investigate_historical_cmus()