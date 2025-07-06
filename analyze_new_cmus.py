#!/usr/bin/env python3
"""
Analyze what companies are in the new CMU data that's not yet in the database
"""
import os
import django
import requests
from collections import Counter

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component

def analyze_new_cmus():
    # Get existing CMU IDs from database
    print("Fetching existing CMU IDs from database...")
    existing_cmu_ids = set(Component.objects.values_list('cmu_id', flat=True).distinct())
    print(f"Found {len(existing_cmu_ids)} existing CMU IDs in database")
    
    # Fetch ALL CMU data from API to get accurate counts
    print("\nFetching CMU data from NESO API...")
    all_cmus = []
    offset = 0
    limit = 10000  # Large batch size
    
    while True:
        url = "https://api.neso.energy/api/3/action/datastore_search"
        params = {
            "resource_id": "25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6",
            "limit": limit,
            "offset": offset
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get("success") and data.get("result", {}).get("records"):
                records = data["result"]["records"]
                all_cmus.extend(records)
                print(f"  Fetched {len(records)} records (total: {len(all_cmus)})")
                
                if len(records) < limit:
                    break
                offset += limit
            else:
                break
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
    
    print(f"\nTotal CMUs from API: {len(all_cmus)}")
    
    # Filter to only new CMUs - using correct field name
    api_cmu_ids = {cmu.get('CMU ID') for cmu in all_cmus if cmu.get('CMU ID')}
    new_cmu_ids = api_cmu_ids - existing_cmu_ids
    new_cmus = [cmu for cmu in all_cmus if cmu.get('CMU ID') in new_cmu_ids]
    
    print(f"API CMU IDs: {len(api_cmu_ids)}")
    print(f"Database CMU IDs: {len(existing_cmu_ids)}")
    print(f"New CMUs not in database: {len(new_cmus)}")
    
    # Debug: show some sample CMUs
    print("\nSample of first 5 CMUs from API:")
    for cmu in all_cmus[:5]:
        print(f"  CMU ID: {cmu.get('CMU ID')}, Company: {cmu.get('Name of Applicant')}, Name: {cmu.get('CM Unit Name')}")
    
    # Analyze company distribution
    company_counter = Counter()
    octopus_cmus = []
    axle_cmus = []
    flexitricity_cmus = []
    gridbeyond_cmus = []
    
    for cmu in new_cmus:
        company = cmu.get('Name of Applicant', 'Unknown')
        company_counter[company] += 1
        
        # Check for specific companies
        if 'octopus' in company.lower():
            octopus_cmus.append(cmu)
        if 'axle' in company.lower():
            axle_cmus.append(cmu)
        if 'flexitricity' in company.lower():
            flexitricity_cmus.append(cmu)
        if 'gridbeyond' in company.lower():
            gridbeyond_cmus.append(cmu)
    
    # Print results
    print(f"\n{'='*60}")
    print("NEW CMU ANALYSIS RESULTS")
    print(f"{'='*60}")
    
    print(f"\nOctopus Energy: {len(octopus_cmus)} new CMUs")
    if octopus_cmus:
        for cmu in octopus_cmus[:5]:  # Show first 5
            print(f"  - {cmu.get('CMU ID')}: {cmu.get('CM Unit Name', 'N/A')}")
    
    print(f"\nAxle Energy: {len(axle_cmus)} new CMUs")
    if axle_cmus:
        for cmu in axle_cmus[:5]:  # Show first 5
            print(f"  - {cmu.get('CMU ID')}: {cmu.get('CM Unit Name', 'N/A')}")
    
    print(f"\nFlexitricity: {len(flexitricity_cmus)} new CMUs")
    print(f"GridBeyond: {len(gridbeyond_cmus)} new CMUs")
    
    print("\nTop 20 companies by new CMU count:")
    for company, count in company_counter.most_common(20):
        percentage = (count / len(new_cmus)) * 100
        print(f"  {company}: {count} CMUs ({percentage:.1f}%)")
    
    # Check fuel types for battery storage
    fuel_counter = Counter()
    battery_cmus = []
    
    for cmu in new_cmus:
        fuel = cmu.get('Primary Fuel Type', 'Unknown')
        fuel_counter[fuel] += 1
        storage_facility = cmu.get('Storage Facility', 'No')
        if 'battery' in str(fuel).lower() or 'storage' in str(fuel).lower() or storage_facility == 'Yes':
            battery_cmus.append(cmu)
    
    print(f"\n{'='*60}")
    print("FUEL TYPE ANALYSIS OF NEW CMUs")
    print(f"{'='*60}")
    
    print(f"\nBattery Storage CMUs: {len(battery_cmus)}")
    
    print("\nAll fuel types in new CMUs:")
    for fuel, count in fuel_counter.most_common():
        percentage = (count / len(new_cmus)) * 100
        print(f"  {fuel}: {count} CMUs ({percentage:.1f}%)")
    
    # Show battery storage companies
    if battery_cmus:
        battery_companies = Counter()
        for cmu in battery_cmus:
            battery_companies[cmu.get('Name of Applicant', 'Unknown')] += 1
        
        print("\nTop battery storage companies in new CMUs:")
        for company, count in battery_companies.most_common(10):
            print(f"  {company}: {count} battery CMUs")

if __name__ == "__main__":
    analyze_new_cmus()