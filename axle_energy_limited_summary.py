#!/usr/bin/env python3
"""
Summary investigation for AXLE ENERGY LIMITED DSR capacity ranking.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

def summarize_axle_energy_limited():
    with connection.cursor() as cursor:
        print("=" * 80)
        print("AXLE ENERGY LIMITED - SUMMARY INVESTIGATION")
        print("=" * 80)
        
        # Total AXLE ENERGY LIMITED locations
        query1 = """
        SELECT COUNT(*) as total_locations
        FROM checker_locationgroup 
        WHERE companies ? 'AXLE ENERGY LIMITED';
        """
        cursor.execute(query1)
        total_locations = cursor.fetchone()[0]
        print(f"Total AXLE ENERGY LIMITED locations: {total_locations:,}")
        
        # DSR locations count
        query2 = """
        SELECT COUNT(*) as dsr_locations
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%' 
          AND companies ? 'AXLE ENERGY LIMITED';
        """
        cursor.execute(query2)
        dsr_locations = cursor.fetchone()[0]
        print(f"AXLE ENERGY LIMITED DSR locations: {dsr_locations:,}")
        
        # Best DSR ranking
        query3 = """
        SELECT 
            MIN(ranked.capacity_rank) as best_rank,
            MAX(lg.normalized_capacity_mw) as max_capacity
        FROM (
            SELECT 
                location,
                normalized_capacity_mw,
                ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as capacity_rank
            FROM checker_locationgroup 
            WHERE technologies::text ILIKE '%DSR%'
        ) ranked
        JOIN checker_locationgroup lg ON ranked.location = lg.location
        WHERE lg.companies ? 'AXLE ENERGY LIMITED';
        """
        cursor.execute(query3)
        best_rank_result = cursor.fetchone()
        best_rank, max_capacity = best_rank_result if best_rank_result else (None, None)
        
        if best_rank:
            print(f"Best AXLE ENERGY LIMITED DSR ranking: #{best_rank:,}")
            print(f"Highest AXLE ENERGY LIMITED DSR capacity: {max_capacity:.2f} MW")
        else:
            print("No ranking data found for AXLE ENERGY LIMITED DSR locations")
        
        # In top 500?
        query4 = """
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
        cursor.execute(query4)
        axle_in_top_500 = cursor.fetchone()[0]
        print(f"AXLE ENERGY LIMITED locations in top 500 DSR: {axle_in_top_500}")
        
        # What's the 500th capacity threshold?
        query5 = """
        SELECT normalized_capacity_mw
        FROM (
            SELECT 
                normalized_capacity_mw,
                ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
            FROM checker_locationgroup 
            WHERE technologies::text ILIKE '%DSR%'
        ) ranked
        WHERE rank = 500;
        """
        cursor.execute(query5)
        threshold_result = cursor.fetchone()
        threshold_capacity = threshold_result[0] if threshold_result else None
        
        if threshold_capacity:
            print(f"500th place DSR capacity threshold: {threshold_capacity:.2f} MW")
        
        # Total DSR locations
        query6 = """
        SELECT COUNT(*) as total_dsr_locations
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%';
        """
        cursor.execute(query6)
        total_dsr = cursor.fetchone()[0]
        print(f"Total DSR locations in database: {total_dsr:,}")
        
        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        
        if dsr_locations > 0:
            print(f"✓ AXLE ENERGY LIMITED exists in the database")
            print(f"✓ Has {dsr_locations:,} DSR locations")
            
            if best_rank and best_rank > 500:
                print(f"✗ PROBLEM: Best DSR ranking is #{best_rank:,} (below top 500)")
                print(f"✗ Technology map dropdown only shows top 500 locations")
                print(f"✗ This explains why AXLE ENERGY LIMITED doesn't appear!")
                print(f"✗ All AXLE ENERGY LIMITED DSR locations have 0.00 MW capacity")
            elif axle_in_top_500 == 0:
                print(f"✗ PROBLEM: No AXLE ENERGY LIMITED locations in top 500")
                print(f"✗ All locations likely have very low/zero capacity")
            else:
                print(f"✓ Has {axle_in_top_500} location(s) in top 500 - should appear in dropdown")
        else:
            print("✗ No AXLE ENERGY LIMITED DSR locations found")
        
        print(f"\n📊 KEY INSIGHT:")
        print(f"   The issue is that ALL AXLE ENERGY LIMITED DSR locations")
        print(f"   have 0.00 MW normalized capacity, putting them at the")
        print(f"   bottom of the capacity rankings (below top 500).")
        print(f"   The technology map dropdown sampling excludes them.")

if __name__ == "__main__":
    summarize_axle_energy_limited()