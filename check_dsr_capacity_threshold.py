#!/usr/bin/env python3
"""
Check the capacity threshold for top 500 DSR locations.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
sys.path.append('/Users/davidcrawford/PycharmProjects/cmr')
django.setup()

def check_capacity_threshold():
    with connection.cursor() as cursor:
        print("=" * 80)
        print("DSR CAPACITY THRESHOLD ANALYSIS")
        print("=" * 80)
        
        # Get the capacity distribution around the 500th rank
        query = """
        SELECT 
            rank,
            normalized_capacity_mw,
            location
        FROM (
            SELECT 
                normalized_capacity_mw,
                location,
                ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
            FROM checker_locationgroup 
            WHERE technologies::text ILIKE '%DSR%'
        ) ranked
        WHERE rank BETWEEN 495 AND 505
        ORDER BY rank;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("DSR Capacity Rankings around 500th place:")
        print(f"{'Rank':<6} {'Capacity (MW)':<15} {'Location':<30}")
        print("-" * 51)
        
        for rank, capacity, location in results:
            print(f"{rank:<6} {capacity:<15.2f} {location:<30}")
        
        # Count how many have 0.00 capacity
        query2 = """
        SELECT 
            COUNT(*) as zero_capacity_count,
            (SELECT COUNT(*) FROM checker_locationgroup WHERE technologies::text ILIKE '%DSR%') as total_dsr
        FROM checker_locationgroup 
        WHERE technologies::text ILIKE '%DSR%' 
          AND normalized_capacity_mw = 0.00;
        """
        
        cursor.execute(query2)
        zero_count, total_dsr = cursor.fetchone()
        
        print(f"\n📊 CAPACITY ANALYSIS:")
        print(f"   Total DSR locations: {total_dsr:,}")
        print(f"   Locations with 0.00 MW capacity: {zero_count:,}")
        print(f"   Percentage with 0.00 MW: {(zero_count/total_dsr)*100:.1f}%")
        
        # Check where zero-capacity locations rank
        query3 = """
        SELECT MIN(rank) as first_zero_rank
        FROM (
            SELECT 
                normalized_capacity_mw,
                ROW_NUMBER() OVER (ORDER BY normalized_capacity_mw DESC) as rank
            FROM checker_locationgroup 
            WHERE technologies::text ILIKE '%DSR%'
        ) ranked
        WHERE normalized_capacity_mw = 0.00;
        """
        
        cursor.execute(query3)
        first_zero_rank = cursor.fetchone()[0]
        
        if first_zero_rank:
            print(f"   First 0.00 MW location rank: #{first_zero_rank:,}")
            print(f"   All 0.00 MW locations rank #{first_zero_rank:,} or lower")
            
            if first_zero_rank > 500:
                print(f"   ✗ All 0.00 MW locations are excluded from top 500!")
            else:
                print(f"   ✓ Some 0.00 MW locations are in top 500")

if __name__ == "__main__":
    check_capacity_threshold()