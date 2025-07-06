#!/usr/bin/env python
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def run_query(query, description):
    print(f"\n{'='*60}")
    print(f"QUERY: {description}")
    print(f"{'='*60}")
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()
        
        print(f"Columns: {columns}")
        print(f"Results found: {len(results)}")
        print("-" * 60)
        
        for row in results:
            for i, value in enumerate(row):
                print(f"{columns[i]}: {value}")
            print("-" * 40)
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Query 1: Find all LocationGroups with DSR technology and AXLE ENERGY company
    query1 = """
    SELECT 
        location,
        is_active,
        auction_years,
        technologies,
        companies,
        component_count
    FROM checker_locationgroup 
    WHERE technologies::text ILIKE '%DSR%' 
      AND companies::text ILIKE '%AXLE ENERGY%'
    ORDER BY location;
    """
    
    # Query 2: Check individual components for AXLE ENERGY + DSR
    query2 = """
    SELECT 
        location,
        company_name,
        technology,
        auction_name,
        delivery_year,
        cmu_id
    FROM checker_component 
    WHERE company_name ILIKE '%AXLE ENERGY%' 
      AND technology ILIKE '%DSR%'
    ORDER BY location, auction_name;
    """
    
    # Query 3: Check if there are components without corresponding LocationGroups
    query3 = """
    SELECT 
        c.location,
        COUNT(*) as component_count,
        STRING_AGG(DISTINCT c.auction_name, ', ') as auction_years,
        CASE WHEN lg.location IS NULL THEN 'Missing LocationGroup' ELSE 'Has LocationGroup' END as status
    FROM checker_component c
    LEFT JOIN checker_locationgroup lg ON c.location = lg.location
    WHERE c.company_name ILIKE '%AXLE ENERGY%' 
      AND c.technology ILIKE '%DSR%'
    GROUP BY c.location, lg.location
    ORDER BY c.location;
    """
    
    try:
        run_query(query1, "LocationGroups with DSR + AXLE ENERGY")
        run_query(query2, "Individual components for AXLE ENERGY + DSR")
        run_query(query3, "Components without LocationGroups")
        
    except Exception as e:
        print(f"Error running queries: {e}")
        import traceback
        traceback.print_exc()