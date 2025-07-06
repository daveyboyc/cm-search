#!/usr/bin/env python3
"""
Check AXLE ENERGY LIMITED specifically in the database.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

def check_axle_energy_limited():
    with connection.cursor() as cursor:
        print("=" * 80)
        print("AXLE ENERGY LIMITED INVESTIGATION")
        print("=" * 80)
        
        # Check AXLE ENERGY LIMITED in LocationGroup
        print("\n1. AXLE ENERGY LIMITED in LocationGroup:")
        print("-" * 45)
        
        query1 = """
        SELECT 
            location,
            technologies,
            (companies->>'AXLE ENERGY LIMITED')::int as axle_count,
            normalized_capacity_mw,
            ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as capacity_rank
        FROM checker_locationgroup 
        WHERE companies ? 'AXLE ENERGY LIMITED'
        ORDER BY normalized_capacity_mw DESC;
        """
        
        cursor.execute(query1)
        results1 = cursor.fetchall()
        
        if results1:
            print(f"Found {len(results1)} AXLE ENERGY LIMITED locations:")
            print(f"{'Location':<40} {'Technologies':<15} {'Count':<8} {'Capacity':<12} {'Rank':<8}")
            print("-" * 88)
            for location, technologies, count, capacity, rank in results1:
                tech_str = str(technologies)[:13] + "..." if len(str(technologies)) > 15 else str(technologies)
                print(f"{location:<40} {tech_str:<15} {count:<8} {capacity:<12.2f} {rank:<8}")
        else:
            print("No AXLE ENERGY LIMITED locations found in LocationGroup!")
        
        # Check AXLE ENERGY LIMITED in DSR specifically
        print("\n\n2. AXLE ENERGY LIMITED DSR locations:")
        print("-" * 40)
        
        query2 = """
        SELECT 
            location,
            (companies->>'AXLE ENERGY LIMITED')::int as axle_count,
            normalized_capacity_mw,
            ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as capacity_rank
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%' 
          AND companies ? 'AXLE ENERGY LIMITED'
        ORDER BY normalized_capacity_mw DESC;
        """
        
        cursor.execute(query2)
        dsr_results = cursor.fetchall()
        
        if dsr_results:
            print(f"Found {len(dsr_results)} AXLE ENERGY LIMITED DSR locations:")
            print(f"{'Location':<40} {'Count':<8} {'Capacity':<12} {'DSR Rank':<10}")
            print("-" * 70)
            for location, count, capacity, rank in dsr_results:
                print(f"{location:<40} {count:<8} {capacity:<12.2f} {rank:<10}")
        else:
            print("No AXLE ENERGY LIMITED DSR locations found!")
        
        # Check if any AXLE ENERGY LIMITED DSR locations are in top 500
        print("\n\n3. AXLE ENERGY LIMITED in top 500 DSR locations:")
        print("-" * 55)
        
        query3 = """
        SELECT COUNT(*) as axle_in_top_500
        FROM (
            SELECT location
            FROM checker_locationgroup 
            WHERE technologies::text ILIKE '%DSR%'
            ORDER BY normalized_capacity_mw DESC
            LIMIT 500
        ) top_500
        JOIN checker_locationgroup lg ON top_500.location = lg.location
        WHERE lg.companies ? 'AXLE ENERGY LIMITED';
        """
        
        cursor.execute(query3)
        axle_in_top_500 = cursor.fetchone()[0]
        print(f"AXLE ENERGY LIMITED locations in top 500 DSR: {axle_in_top_500}")
        
        # Check Component table
        print("\n\n4. AXLE ENERGY LIMITED in Component table:")
        print("-" * 45)
        
        query4 = """
        SELECT 
            technology,
            COUNT(*) as component_count,
            SUM(derated_capacity_mw) as total_capacity
        FROM checker_component 
        WHERE company_name = 'AXLE ENERGY LIMITED'
        GROUP BY technology
        ORDER BY total_capacity DESC;
        """
        
        cursor.execute(query4)
        component_results = cursor.fetchall()
        
        if component_results:
            print("AXLE ENERGY LIMITED components:")
            print(f"{'Technology':<20} {'Count':<10} {'Total Capacity (MW)':<20}")
            print("-" * 50)
            for technology, count, capacity in component_results:
                capacity_val = capacity or 0
                print(f"{technology:<20} {count:<10} {capacity_val:<20.2f}")
        else:
            print("No AXLE ENERGY LIMITED components found!")

        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        
        if dsr_results:
            best_rank = min(row[3] for row in dsr_results)
            if axle_in_top_500 == 0:
                print("🔍 ISSUE IDENTIFIED:")
                print(f"  - AXLE ENERGY LIMITED has {len(dsr_results)} DSR location(s)")
                print(f"  - Best DSR location rank: #{best_rank}")
                print(f"  - BUT none are in top 500 by capacity")
                print(f"  - Technology map dropdown only shows top 500 locations")
                print(f"  - This explains why AXLE ENERGY LIMITED doesn't appear!")
            else:
                print("✓ AXLE ENERGY LIMITED should appear in DSR dropdown")
                print(f"  - Has {axle_in_top_500} location(s) in top 500")
        elif component_results:
            print("🔍 POTENTIAL ISSUE:")
            print("  - AXLE ENERGY LIMITED exists in Component table")
            print("  - But NOT in LocationGroup (aggregated data)")
            print("  - This suggests a data aggregation issue")
        else:
            print("✗ AXLE ENERGY LIMITED completely missing from database!")

if __name__ == "__main__":
    check_axle_energy_limited()