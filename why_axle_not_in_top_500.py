#!/usr/bin/env python3
"""
Investigate why AXLE ENERGY LIMITED DSR locations aren't in top 500 
when most DSR locations have 0.00 MW capacity.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

def investigate_top_500_criteria():
    with connection.cursor() as cursor:
        print("=" * 80)
        print("WHY AXLE ENERGY LIMITED NOT IN TOP 500 DSR INVESTIGATION")
        print("=" * 80)
        
        # Check the exact ranking criteria - there might be a secondary sort
        query1 = """
        SELECT 
            location,
            normalized_capacity_mw,
            ROW_NUMBER() OVER (
                ORDER BY normalized_capacity_mw DESC, location ASC
            ) as rank_with_location_tiebreaker,
            ROW_NUMBER() OVER (
                ORDER BY normalized_capacity_mw DESC
            ) as rank_capacity_only
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%'
          AND companies ? 'AXLE ENERGY LIMITED'
        ORDER BY normalized_capacity_mw DESC, location ASC
        LIMIT 10;
        """
        
        cursor.execute(query1)
        axle_results = cursor.fetchall()
        
        print("AXLE ENERGY LIMITED DSR locations with different ranking methods:")
        print(f"{'Location':<25} {'Capacity':<12} {'Rank (w/tie)':<12} {'Rank (cap only)':<15}")
        print("-" * 64)
        
        for location, capacity, rank_tie, rank_cap in axle_results:
            print(f"{location:<25} {capacity:<12.2f} {rank_tie:<12} {rank_cap:<15}")
        
        # Check what the actual query used by the technology map looks like
        print(f"\n📊 TECHNOLOGY MAP QUERY ANALYSIS:")
        
        query2 = """
        SELECT location
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%'
        ORDER BY normalized_capacity_mw DESC
        LIMIT 500;
        """
        
        cursor.execute(query2)
        top_500_locations = [row[0] for row in cursor.fetchall()]
        
        # Check if any AXLE locations are in this list
        axle_locations_in_top_500 = []
        for location, _, _, _ in axle_results:
            if location in top_500_locations:
                axle_locations_in_top_500.append(location)
        
        print(f"   Top 500 query returns {len(top_500_locations)} locations")
        print(f"   AXLE ENERGY LIMITED locations in result: {len(axle_locations_in_top_500)}")
        
        if axle_locations_in_top_500:
            print(f"   AXLE locations found: {axle_locations_in_top_500[:5]}...")
        
        # Let's check the tie-breaking behavior with a focused query
        query3 = """
        WITH ranked_dsr AS (
            SELECT 
                location,
                normalized_capacity_mw,
                companies ? 'AXLE ENERGY LIMITED' as is_axle,
                ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
            FROM checker_locationgroup 
            WHERE technologies::text ILIKE '%DSR%'
        )
        SELECT 
            COUNT(*) as total_in_top_500,
            SUM(CASE WHEN is_axle THEN 1 ELSE 0 END) as axle_in_top_500
        FROM ranked_dsr
        WHERE rank <= 500;
        """
        
        cursor.execute(query3)
        total_500, axle_500 = cursor.fetchone()
        
        print(f"   Verification: {axle_500} AXLE locations in top 500 of {total_500}")
        
        # Check if there's a specific ordering issue
        query4 = """
        SELECT location, normalized_capacity_mw, 
               ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%'
          AND normalized_capacity_mw = 0.00
          AND companies ? 'AXLE ENERGY LIMITED'
        ORDER BY rank
        LIMIT 5;
        """
        
        cursor.execute(query4)
        axle_zero_rankings = cursor.fetchall()
        
        print(f"\nAXLE ENERGY LIMITED 0.00 MW locations rankings:")
        print(f"{'Location':<25} {'Capacity':<12} {'Rank':<8}")
        print("-" * 45)
        
        for location, capacity, rank in axle_zero_rankings:
            print(f"{location:<25} {capacity:<12.2f} {rank:<8}")
        
        # The key insight: check if PostgreSQL's ordering is non-deterministic for ties
        print(f"\n🔍 ROOT CAUSE ANALYSIS:")
        
        if axle_zero_rankings and axle_zero_rankings[0][2] > 500:
            print(f"   ✗ AXLE ENERGY LIMITED's best 0.00 MW location ranks #{axle_zero_rankings[0][2]:,}")
            print(f"   ✗ This is beyond the top 500 cutoff")
            print(f"   ✗ When there are many tied 0.00 MW values, PostgreSQL's")
            print(f"     ORDER BY without explicit tie-breaking is non-deterministic")
            print(f"   ✗ AXLE ENERGY LIMITED locations happen to sort later in the")
            print(f"     tie-breaking, pushing them beyond position 500")
        else:
            print(f"   ✓ AXLE ENERGY LIMITED locations should be in top 500")
            print(f"   ❓ There may be another filtering issue")

if __name__ == "__main__":
    investigate_top_500_criteria()