#!/usr/bin/env python3
"""
Investigation script for AXLE ENERGY DSR capacity ranking issue.
This script checks why AXLE ENERGY might not appear in the technology map dropdown.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

def run_investigation():
    with connection.cursor() as cursor:
        print("=" * 80)
        print("AXLE ENERGY DSR CAPACITY RANKING INVESTIGATION")
        print("=" * 80)
        
        # Query 1: Check AXLE ENERGY's ranking among DSR locations by capacity
        print("\n1. AXLE ENERGY DSR locations with capacity ranking:")
        print("-" * 60)
        
        query1 = """
        SELECT 
            location,
            (companies->>'AXLE ENERGY')::int as axle_count,
            normalized_capacity_mw,
            ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as capacity_rank
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%' 
          AND companies ? 'AXLE ENERGY'
        ORDER BY normalized_capacity_mw DESC
        LIMIT 20;
        """
        
        cursor.execute(query1)
        results1 = cursor.fetchall()
        
        if results1:
            print(f"{'Location':<40} {'Count':<8} {'Capacity (MW)':<15} {'Rank':<8}")
            print("-" * 71)
            for row in results1:
                location, count, capacity, rank = row
                print(f"{location:<40} {count:<8} {capacity:<15.2f} {rank:<8}")
        else:
            print("No AXLE ENERGY DSR locations found!")
        
        # Query 2: Count total DSR locations
        print("\n\n2. Total DSR locations in database:")
        print("-" * 40)
        
        query2 = """
        SELECT COUNT(*) as total_dsr_locations
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%';
        """
        
        cursor.execute(query2)
        total_dsr = cursor.fetchone()[0]
        print(f"Total DSR locations: {total_dsr:,}")
        
        # Query 3: Check if AXLE ENERGY appears in top 500
        print("\n\n3. AXLE ENERGY presence in top 500 DSR locations by capacity:")
        print("-" * 70)
        
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
        WHERE lg.companies ? 'AXLE ENERGY';
        """
        
        cursor.execute(query3)
        axle_in_top_500 = cursor.fetchone()[0]
        print(f"AXLE ENERGY locations in top 500: {axle_in_top_500}")
        
        # Query 4: Get the 500th ranked DSR location capacity for comparison
        print("\n\n4. Capacity threshold for top 500 DSR locations:")
        print("-" * 55)
        
        query4 = """
        SELECT normalized_capacity_mw, 
               ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%'
        ORDER BY normalized_capacity_mw DESC
        LIMIT 500
        """
        
        cursor.execute(query4)
        top_500_results = cursor.fetchall()
        
        if len(top_500_results) >= 500:
            threshold_capacity = top_500_results[499][1]  # 500th item (0-indexed)
            print(f"500th ranked DSR location capacity: {threshold_capacity:.2f} MW")
        else:
            print(f"Only {len(top_500_results)} DSR locations exist (less than 500)")
        
        # Query 5: Top 10 DSR companies by total capacity
        print("\n\n5. Top 10 DSR companies by total capacity:")
        print("-" * 50)
        
        query5 = """
        WITH company_totals AS (
            SELECT 
                company_name,
                SUM(normalized_capacity_mw * company_count) as total_capacity
            FROM (
                SELECT 
                    jsonb_each_text(companies) as company_data,
                    normalized_capacity_mw
                FROM checker_locationgroup 
                WHERE technologies::text ILIKE '%DSR%'
            ) expanded,
            LATERAL (
                SELECT 
                    (company_data).key as company_name,
                    ((company_data).value)::int as company_count
            ) parsed
            GROUP BY company_name
        )
        SELECT 
            company_name,
            total_capacity,
            ROW_NUMBER() OVER (ORDER BY total_capacity DESC) as rank
        FROM company_totals
        ORDER BY total_capacity DESC
        LIMIT 10;
        """
        
        cursor.execute(query5)
        top_companies = cursor.fetchall()
        
        print(f"{'Rank':<6} {'Company':<40} {'Total Capacity (MW)':<20}")
        print("-" * 66)
        for company, capacity, rank in top_companies:
            print(f"{rank:<6} {company:<40} {capacity:<20.2f}")
        
        # Query 6: Check AXLE ENERGY's total DSR capacity ranking
        print("\n\n6. AXLE ENERGY's ranking among all DSR companies:")
        print("-" * 55)
        
        query6 = """
        WITH company_totals AS (
            SELECT 
                company_name,
                SUM(normalized_capacity_mw * company_count) as total_capacity
            FROM (
                SELECT 
                    jsonb_each_text(companies) as company_data,
                    normalized_capacity_mw
                FROM checker_locationgroup 
                WHERE technologies::text ILIKE '%DSR%'
            ) expanded,
            LATERAL (
                SELECT 
                    (company_data).key as company_name,
                    ((company_data).value)::int as company_count
            ) parsed
            GROUP BY company_name
        ),
        ranked_companies AS (
            SELECT 
                company_name,
                total_capacity,
                ROW_NUMBER() OVER (ORDER BY total_capacity DESC) as rank
            FROM company_totals
        )
        SELECT company_name, total_capacity, rank
        FROM ranked_companies
        WHERE company_name = 'AXLE ENERGY';
        """
        
        cursor.execute(query6)
        axle_ranking = cursor.fetchone()
        
        if axle_ranking:
            company, capacity, rank = axle_ranking
            print(f"AXLE ENERGY total DSR capacity: {capacity:.2f} MW")
            print(f"AXLE ENERGY ranking among DSR companies: #{rank}")
        else:
            print("AXLE ENERGY not found in DSR company rankings!")
        
        print("\n" + "=" * 80)
        print("INVESTIGATION SUMMARY")
        print("=" * 80)
        
        if results1:
            highest_rank = min(row[3] for row in results1)  # Get the best (lowest) rank
            print(f"✓ AXLE ENERGY has {len(results1)} DSR location(s)")
            print(f"✓ Best AXLE ENERGY DSR location rank: #{highest_rank}")
            
            if axle_in_top_500 == 0:
                print(f"✗ PROBLEM FOUND: No AXLE ENERGY DSR locations in top 500!")
                print(f"  This explains why AXLE ENERGY doesn't appear in the dropdown.")
                print(f"  The technology map uses sampling (top 500) to populate dropdowns.")
            else:
                print(f"✓ AXLE ENERGY has {axle_in_top_500} location(s) in top 500")
        else:
            print("✗ CRITICAL: No AXLE ENERGY DSR locations found at all!")

if __name__ == "__main__":
    run_investigation()