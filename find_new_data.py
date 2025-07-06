import requests
import os
import django
from collections import defaultdict, Counter
from datetime import datetime

# Setup Django to access your database
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component

def find_legitimate_new_data():
    """Find what new data actually exists, filtering out duplicates"""
    
    print("🔍 FINDING LEGITIMATE NEW DATA")
    print("="*50)
    
    # 1. Get your current component IDs and CMU IDs
    print("📊 Analyzing your current database...")
    
    your_component_ids = set(Component.objects.values_list('component_id', flat=True))
    your_cmu_ids = set(Component.objects.values_list('cmu_id', flat=True))
    
    print(f"Your database:")
    print(f"  Components: {len(your_component_ids):,}")
    print(f"  Unique CMU IDs: {len(your_cmu_ids):,}")
    
    # 2. Sample API data to find genuinely new items
    component_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
    component_resource_id = '790f5fa0-f8eb-4d82-b98d-0d34d3e404e8'
    
    print(f"\n🆕 CHECKING FOR NEW DATA IN API...")
    
    new_component_ids = set()
    new_cmu_ids = set()
    seen_component_ids = set()  # Track duplicates in API
    api_duplicates = 0
    
    # Sample recent data (get several batches)
    for offset in range(0, 5000, 1000):  # Check 5000 recent records
        params = {
            'resource_id': component_resource_id,
            'limit': 1000,
            'offset': offset,
            'sort': '_id desc'  # Get newest first
        }
        
        try:
            response = requests.get(component_api_url, params=params, timeout=30)
            data = response.json()
            
            if not data.get('success'):
                break
                
            records = data.get('result', {}).get('records', [])
            if not records:
                break
                
            for record in records:
                component_id = record.get('Component ID')
                cmu_id = record.get('CMU ID')
                
                if not component_id or not cmu_id:
                    continue
                
                # Check for API duplicates
                if component_id in seen_component_ids:
                    api_duplicates += 1
                    continue
                seen_component_ids.add(component_id)
                
                # Check if this is new to your database
                if component_id not in your_component_ids:
                    new_component_ids.add(component_id)
                
                if cmu_id not in your_cmu_ids:
                    new_cmu_ids.add(cmu_id)
            
            print(f"  Processed offset {offset}...")
            
        except Exception as e:
            print(f"Error at offset {offset}: {e}")
            break
    
    print(f"\n📈 ANALYSIS RESULTS:")
    print(f"API duplicates found: {api_duplicates}")
    print(f"Unique API records processed: {len(seen_component_ids):,}")
    print(f"New Component IDs: {len(new_component_ids):,}")
    print(f"New CMU IDs: {len(new_cmu_ids):,}")
    
    # 3. Analyze the new CMUs to understand what they are
    if new_cmu_ids:
        print(f"\n🆕 ANALYZING NEW CMU IDs:")
        
        cmu_api_url = 'https://api.neso.energy/api/3/action/datastore_search'
        cmu_resource_id = '25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6'
        
        new_cmu_companies = Counter()
        new_cmu_auctions = Counter()
        
        # Check a sample of new CMUs
        for cmu_id in list(new_cmu_ids)[:20]:
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
                        
                        new_cmu_companies[company] += 1
                        new_cmu_auctions[auction] += 1
                        
                        print(f"  {cmu_id}: {company} ({auction})")
                        
            except Exception as e:
                print(f"Error checking {cmu_id}: {e}")
        
        print(f"\n📊 NEW CMU PATTERNS:")
        print(f"Top companies in new CMUs:")
        for company, count in new_cmu_companies.most_common(10):
            print(f"  {company}: {count}")
            
        print(f"\nAuctions in new CMUs:")
        for auction, count in new_cmu_auctions.most_common(10):
            print(f"  {auction}: {count}")
    
    # 4. Check what your latest data is
    print(f"\n📅 YOUR LATEST DATA:")
    latest_components = Component.objects.order_by('-created_at')[:5]
    for comp in latest_components:
        print(f"  {comp.cmu_id} ({comp.component_id}) - added {comp.created_at.strftime('%Y-%m-%d')}")
    
    latest_auction = Component.objects.values('auction_name').annotate(
        count=models.Count('id')
    ).order_by('-auction_name').first()
    
    if latest_auction:
        print(f"\nLatest auction in your DB: {latest_auction['auction_name']}")
    
    # 5. Estimate actual new data worth crawling
    print(f"\n🎯 RECOMMENDATION:")
    if len(new_component_ids) < 1000:
        print(f"✅ Only {len(new_component_ids)} truly new components found")
        print(f"   This suggests your database is quite up-to-date")
    elif len(new_component_ids) < 10000:
        print(f"⚠️  {len(new_component_ids)} new components found")
        print(f"   A targeted crawl for new CMUs might be worthwhile")
    else:
        print(f"🚨 {len(new_component_ids)} new components found")
        print(f"   Consider a more comprehensive crawl")
    
    return {
        'new_components': len(new_component_ids),
        'new_cmus': len(new_cmu_ids),
        'api_duplicates': api_duplicates,
        'companies': dict(new_cmu_companies),
        'auctions': dict(new_cmu_auctions)
    }

if __name__ == "__main__":
    from django.db import models
    result = find_legitimate_new_data()