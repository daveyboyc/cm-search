#!/usr/bin/env python3
"""
Verification script to check if AXLE ENERGY exists in any technology, not just DSR.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

def verify_axle_energy():
    with connection.cursor() as cursor:
        print("=" * 80)
        print("AXLE ENERGY EXISTENCE VERIFICATION")
        print("=" * 80)
        
        # Check if AXLE ENERGY exists in any LocationGroup
        print("\n1. AXLE ENERGY in any LocationGroup:")
        print("-" * 40)
        
        query1 = """
        SELECT 
            location,
            technologies,
            (companies->>'AXLE ENERGY')::int as axle_count,
            normalized_capacity_mw
        FROM checker_locationgroup 
        WHERE companies ? 'AXLE ENERGY'
        ORDER BY normalized_capacity_mw DESC
        LIMIT 10;
        """
        
        cursor.execute(query1)
        results1 = cursor.fetchall()
        
        if results1:
            print(f"Found {len(results1)} AXLE ENERGY locations in LocationGroup:")
            print(f"{'Location':<40} {'Technologies':<30} {'Count':<8} {'Capacity':<12}")
            print("-" * 90)
            for location, technologies, count, capacity in results1:
                tech_str = str(technologies)[:28] + "..." if len(str(technologies)) > 30 else str(technologies)
                print(f"{location:<40} {tech_str:<30} {count:<8} {capacity:<12.2f}")
        else:
            print("No AXLE ENERGY locations found in LocationGroup!")
        
        # Check if AXLE ENERGY exists in Component table
        print("\n\n2. AXLE ENERGY in Component table:")
        print("-" * 35)
        
        query2 = """
        SELECT 
            COUNT(*) as total_components,
            technology,
            SUM(derated_capacity_mw) as total_capacity
        FROM checker_component 
        WHERE company_name = 'AXLE ENERGY'
        GROUP BY technology
        ORDER BY total_capacity DESC;
        """
        
        cursor.execute(query2)
        component_results = cursor.fetchall()
        
        if component_results:
            print("AXLE ENERGY components found:")
            print(f"{'Technology':<20} {'Count':<10} {'Total Capacity (MW)':<20}")
            print("-" * 50)
            for count, technology, capacity in component_results:
                capacity_val = capacity or 0
                print(f"{technology:<20} {count:<10} {capacity_val:<20.2f}")
        else:
            print("No AXLE ENERGY components found in Component table!")
        
        # Check all unique company names that contain "AXLE"
        print("\n\n3. All companies containing 'AXLE':")
        print("-" * 40)
        
        query3 = """
        SELECT DISTINCT company_name
        FROM checker_component 
        WHERE company_name ILIKE '%AXLE%'
        ORDER BY company_name;
        """
        
        cursor.execute(query3)
        axle_companies = cursor.fetchall()
        
        if axle_companies:
            print("Companies containing 'AXLE':")
            for (company,) in axle_companies:
                print(f"  - {company}")
        else:
            print("No companies containing 'AXLE' found!")
        
        # Check LocationGroup companies containing "AXLE"
        print("\n\n4. LocationGroup companies containing 'AXLE':")
        print("-" * 50)
        
        query4 = """
        SELECT DISTINCT company_key
        FROM (
            SELECT jsonb_object_keys(companies) as company_key
            FROM checker_locationgroup
        ) keys
        WHERE company_key ILIKE '%AXLE%'
        ORDER BY company_key;
        """
        
        cursor.execute(query4)
        lg_axle_companies = cursor.fetchall()
        
        if lg_axle_companies:
            print("LocationGroup companies containing 'AXLE':")
            for (company,) in lg_axle_companies:
                print(f"  - {company}")
        else:
            print("No LocationGroup companies containing 'AXLE' found!")

        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        
        if not results1 and not component_results:
            print("✗ AXLE ENERGY does NOT exist in the database at all!")
            print("  This explains why it doesn't appear in any dropdown.")
            print("  The company may have been:")
            print("  1. Renamed or acquired")
            print("  2. Never imported into the database")
            print("  3. Using a different company name variation")
        elif component_results and not results1:
            print("✓ AXLE ENERGY exists in Component table")
            print("✗ AXLE ENERGY does NOT exist in LocationGroup table")
            print("  This suggests the LocationGroup aggregation may have missed this company")
        else:
            print("✓ AXLE ENERGY exists in the database")

if __name__ == "__main__":
    verify_axle_energy()