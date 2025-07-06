#!/usr/bin/env python3
"""
Analyze new CMU data from NESO API to understand company distribution
"""

import os
import sys
import django
import requests
import json
from collections import Counter
import random

# Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component


def fetch_neso_cmu_data():
    """Fetch CMU data from NESO API"""
    print("Fetching CMU data from NESO API...")
    
    # Try both possible API endpoints
    urls = [
        "https://api.nationalgrideso.com/api/3/action/datastore_search",
        "https://data.nationalgrideso.com/api/3/action/datastore_search"
    ]
    
    params = {
        'resource_id': '25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6',
        'limit': 5000  # Get a good sample
    }
    
    for url in urls:
        try:
            print(f"Trying URL: {url}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data['success']:
                records = data['result']['records']
                print(f"Fetched {len(records)} CMU records from NESO API")
                return records
            else:
                print("API request was not successful")
        except Exception as e:
            print(f"Error with {url}: {e}")
            continue
    
    print("Failed to fetch from API, checking for local CMU data file...")
    
    # Try to load from local file if API fails
    if os.path.exists('cmu_data.json'):
        try:
            with open('cmu_data.json', 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    print(f"Loaded {len(data)} CMU records from local file")
                    return data
                elif isinstance(data, dict) and 'result' in data:
                    records = data['result'].get('records', [])
                    print(f"Loaded {len(records)} CMU records from local file")
                    return records
        except Exception as e:
            print(f"Error loading local file: {e}")
    
    return []


def get_existing_cmu_ids():
    """Get CMU IDs that already exist in our database"""
    print("\nGetting existing CMU IDs from database...")
    
    # Get all unique CMU IDs from our database
    existing_ids = set(Component.objects.values_list('cmu_id', flat=True).distinct())
    existing_ids.discard(None)  # Remove None values
    existing_ids.discard('')    # Remove empty strings
    
    print(f"Found {len(existing_ids)} existing CMU IDs in database")
    return existing_ids


def analyze_new_cmus(neso_records, existing_ids, sample_size=100):
    """Analyze new CMUs that aren't in our database"""
    print("\nAnalyzing new CMUs...")
    
    # Extract CMU IDs from NESO records - handle different field names
    neso_cmu_data = {}
    for record in neso_records:
        # Try different possible field names for CMU ID
        cmu_id = None
        for field in ['BMU ID', 'CMU ID', 'CM Unit ID', 'CM Unit BMU ID']:
            if field in record and record[field]:
                cmu_id = str(record[field]).strip()
                break
        
        if cmu_id:
            neso_cmu_data[cmu_id] = record
    
    # Find new CMU IDs
    neso_ids = set(neso_cmu_data.keys())
    new_ids = neso_ids - existing_ids
    
    print(f"\nTotal NESO CMU IDs: {len(neso_ids)}")
    print(f"New CMU IDs not in database: {len(new_ids)}")
    
    if not new_ids:
        print("No new CMU IDs found!")
        return
    
    # Sample the new IDs to analyze company distribution
    sample_ids = random.sample(list(new_ids), min(sample_size, len(new_ids)))
    print(f"\nSampling {len(sample_ids)} new CMU IDs for company analysis...")
    
    # Count companies
    company_counter = Counter()
    octopus_cmus = []
    axle_cmus = []
    
    for cmu_id in sample_ids:
        record = neso_cmu_data[cmu_id]
        # Try different possible field names for company
        company = None
        for field in ['Company', 'Name of Applicant', 'Parent Company', 'Agent Name']:
            if field in record and record[field]:
                company = str(record[field]).strip()
                break
        
        if not company:
            company = 'Unknown'
            
        company_counter[company] += 1
        
        # Track Octopus and Axle specifically
        if 'octopus' in company.lower():
            octopus_cmus.append((cmu_id, company))
        elif 'axle' in company.lower():
            axle_cmus.append((cmu_id, company))
    
    # Display results
    print("\n" + "="*60)
    print("COMPANY DISTRIBUTION IN NEW CMU DATA")
    print("="*60)
    
    print(f"\nTop 20 companies (from sample of {len(sample_ids)} new CMUs):")
    for company, count in company_counter.most_common(20):
        percentage = (count / len(sample_ids)) * 100
        print(f"  {company}: {count} ({percentage:.1f}%)")
    
    print("\n" + "-"*60)
    print("SPECIFIC COMPANY ANALYSIS")
    print("-"*60)
    
    # Octopus analysis
    octopus_count = sum(1 for c in company_counter if 'octopus' in c.lower())
    octopus_total = sum(company_counter[c] for c in company_counter if 'octopus' in c.lower())
    print(f"\nOctopus Energy:")
    print(f"  Total CMUs: {octopus_total} ({(octopus_total/len(sample_ids))*100:.1f}% of sample)")
    print(f"  Company variations: {octopus_count}")
    if octopus_cmus:
        print("  Sample CMU IDs:")
        for cmu_id, company in octopus_cmus[:5]:
            print(f"    - {cmu_id} ({company})")
    
    # Axle analysis
    axle_count = sum(1 for c in company_counter if 'axle' in c.lower())
    axle_total = sum(company_counter[c] for c in company_counter if 'axle' in c.lower())
    print(f"\nAxle Energy:")
    print(f"  Total CMUs: {axle_total} ({(axle_total/len(sample_ids))*100:.1f}% of sample)")
    print(f"  Company variations: {axle_count}")
    if axle_cmus:
        print("  Sample CMU IDs:")
        for cmu_id, company in axle_cmus[:5]:
            print(f"    - {cmu_id} ({company})")
    
    # Extrapolate to full dataset
    print("\n" + "-"*60)
    print("EXTRAPOLATION TO FULL NEW DATASET")
    print("-"*60)
    print(f"\nBased on sample, estimated totals in {len(new_ids)} new CMUs:")
    print(f"  Octopus Energy: ~{int((octopus_total/len(sample_ids)) * len(new_ids))} CMUs")
    print(f"  Axle Energy: ~{int((axle_total/len(sample_ids)) * len(new_ids))} CMUs")
    
    # Show some example new CMU records
    print("\n" + "-"*60)
    print("SAMPLE NEW CMU RECORDS")
    print("-"*60)
    print("\nExample new CMU records:")
    for i, cmu_id in enumerate(random.sample(list(new_ids), min(5, len(new_ids)))):
        record = neso_cmu_data[cmu_id]
        print(f"\n{i+1}. CMU ID: {cmu_id}")
        
        # Find company name
        company = None
        for field in ['Company', 'Name of Applicant', 'Parent Company']:
            if field in record and record[field]:
                company = record[field]
                break
        print(f"   Company: {company or 'Unknown'}")
        
        # Show other relevant fields
        print(f"   CM Unit Name: {record.get('CM Unit Name', 'Unknown')}")
        print(f"   Fuel Type: {record.get('Primary Fuel Type', record.get('Fuel Type', 'Unknown'))}")
        print(f"   Delivery Year: {record.get('Delivery Year', 'Unknown')}")
        print(f"   CM Unit Type: {record.get('CM Unit Type', 'Unknown')}")
    
    # Do a full scan for Octopus and Axle across ALL new CMUs
    print("\n" + "-"*60)
    print("FULL SCAN FOR OCTOPUS AND AXLE")
    print("-"*60)
    print("\nScanning ALL new CMUs for Octopus and Axle...")
    
    octopus_all = []
    axle_all = []
    
    for cmu_id in new_ids:
        record = neso_cmu_data[cmu_id]
        # Check all text fields for company mentions
        all_text = ' '.join(str(v) for v in record.values() if v).lower()
        
        if 'octopus' in all_text:
            company = None
            for field in ['Company', 'Name of Applicant', 'Parent Company', 'Agent Name']:
                if field in record and record[field]:
                    company = record[field]
                    break
            octopus_all.append({
                'cmu_id': cmu_id,
                'company': company or 'Unknown',
                'cm_unit_name': record.get('CM Unit Name', 'Unknown'),
                'year': record.get('Delivery Year', 'Unknown')
            })
            
        if 'axle' in all_text:
            company = None
            for field in ['Company', 'Name of Applicant', 'Parent Company', 'Agent Name']:
                if field in record and record[field]:
                    company = record[field]
                    break
            axle_all.append({
                'cmu_id': cmu_id,
                'company': company or 'Unknown',
                'cm_unit_name': record.get('CM Unit Name', 'Unknown'),
                'year': record.get('Delivery Year', 'Unknown')
            })
    
    print(f"\nOctopus Energy - Full scan results:")
    print(f"  Found {len(octopus_all)} CMUs mentioning 'Octopus'")
    if octopus_all:
        print("  Details:")
        for item in octopus_all[:10]:  # Show first 10
            print(f"    - {item['cmu_id']}: {item['company']} / {item['cm_unit_name']} (Year: {item['year']})")
        if len(octopus_all) > 10:
            print(f"    ... and {len(octopus_all) - 10} more")
    
    print(f"\nAxle Energy - Full scan results:")
    print(f"  Found {len(axle_all)} CMUs mentioning 'Axle'")
    if axle_all:
        print("  Details:")
        for item in axle_all[:10]:  # Show first 10
            print(f"    - {item['cmu_id']}: {item['company']} / {item['cm_unit_name']} (Year: {item['year']})")
        if len(axle_all) > 10:
            print(f"    ... and {len(axle_all) - 10} more")


def main():
    """Main function"""
    print("CMU Data Analysis Script")
    print("========================\n")
    
    # Fetch NESO data
    neso_records = fetch_neso_cmu_data()
    if not neso_records:
        print("Failed to fetch NESO data")
        return
    
    # Get existing CMU IDs
    existing_ids = get_existing_cmu_ids()
    
    # Analyze new CMUs
    analyze_new_cmus(neso_records, existing_ids, sample_size=200)


if __name__ == "__main__":
    main()