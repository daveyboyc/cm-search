#!/usr/bin/env python
"""
Deep dive analysis of actual egress patterns in search views
Testing O3's assumptions vs reality of Django ORM + PostgreSQL performance
"""
import os
import django
import time
import sys
from django.db import connection
from django.test.utils import override_settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_market_register.settings')
django.setup()

from checker.models import LocationGroup, Component
from django.core.paginator import Paginator
from django.db.models import Count, Sum
import json

def reset_queries():
    """Reset Django's query tracking"""
    connection.queries_log.clear()

def analyze_queries():
    """Analyze executed queries"""
    queries = connection.queries
    total_time = sum(float(q['time']) for q in queries)
    return {
        'count': len(queries),
        'total_time': total_time,
        'queries': queries
    }

def estimate_egress_bytes(data, description=""):
    """Estimate egress bytes for data transfer"""
    if isinstance(data, str):
        size = len(data.encode('utf-8'))
    else:
        size = len(str(data).encode('utf-8'))
    
    print(f"  📊 {description}: {size:,} bytes ({size/1024:.1f} KB)")
    return size

def test_current_search_approach():
    """Test current search view approach (views_search_optimized.py logic)"""
    print("\n" + "="*70)
    print("🔍 TESTING CURRENT SEARCH APPROACH (views_search_optimized.py)")
    print("="*70)
    
    reset_queries()
    start_time = time.time()
    
    # Simulate the current search logic for "all locations"
    location_groups = LocationGroup.objects.all()
    
    # Apply status filter (like the view does)
    status_filter = 'all'
    if status_filter == 'active':
        location_groups = location_groups.filter(is_active=True)
    
    # Get result IDs for filter options (current approach)
    print("1. Getting result IDs for filter generation...")
    reset_queries()
    result_ids = list(location_groups.values_list('id', flat=True))
    ids_analysis = analyze_queries()
    ids_egress = estimate_egress_bytes(result_ids, "Result IDs")
    
    # Get filter options from current results only (current approach)
    print("2. Getting filter options from current results...")
    reset_queries()
    
    if result_ids:
        with connection.cursor() as cursor:
            # Auction years
            cursor.execute("""
                SELECT DISTINCT jsonb_array_elements_text(auction_years::jsonb)
                FROM checker_locationgroup 
                WHERE id = ANY(%s) AND auction_years IS NOT NULL
                ORDER BY 1 DESC
            """, [result_ids])
            auction_years = [row[0] for row in cursor.fetchall()]
            
            # Technologies
            cursor.execute("""
                SELECT DISTINCT jsonb_object_keys(technologies::jsonb)
                FROM checker_locationgroup 
                WHERE id = ANY(%s) AND technologies IS NOT NULL
                ORDER BY 1
            """, [result_ids])
            technologies = [row[0] for row in cursor.fetchall()]
            
            # Companies
            cursor.execute("""
                SELECT DISTINCT jsonb_object_keys(companies::jsonb)
                FROM checker_locationgroup 
                WHERE id = ANY(%s) AND companies IS NOT NULL
                ORDER BY 1
            """, [result_ids])
            companies = [row[0] for row in cursor.fetchall()]
    
    filters_analysis = analyze_queries()
    auction_egress = estimate_egress_bytes(auction_years, "Auction Years")
    tech_egress = estimate_egress_bytes(technologies, "Technologies")
    company_egress = estimate_egress_bytes(companies, "Companies")
    
    # Paginate (like the view does)
    print("3. Paginating results...")
    reset_queries()
    optimized_locations = location_groups.only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    paginator = Paginator(optimized_locations, 25)
    page_obj = paginator.page(1)
    
    pagination_analysis = analyze_queries()
    page_data = list(page_obj)  # Force evaluation
    page_egress = estimate_egress_bytes([{
        'id': loc.id,
        'location': loc.location,
        'county': loc.county,
        'lat': loc.latitude,
        'lng': loc.longitude,
        'descriptions': loc.descriptions,
        'technologies': loc.technologies,
        'companies': loc.companies,
        'auction_years': loc.auction_years,
        'component_count': loc.component_count,
        'capacity': loc.normalized_capacity_mw
    } for loc in page_data], "Page Data (25 items)")
    
    total_time = time.time() - start_time
    total_egress = ids_egress + auction_egress + tech_egress + company_egress + page_egress
    
    print(f"\n📈 CURRENT APPROACH RESULTS:")
    print(f"  ⏱️  Total time: {total_time:.3f}s")
    print(f"  🗃️  Total queries: {ids_analysis['count'] + filters_analysis['count'] + pagination_analysis['count']}")
    print(f"  📤 Total egress: {total_egress:,} bytes ({total_egress/1024:.1f} KB)")
    print(f"  📋 Filter counts: {len(auction_years)} years, {len(technologies)} techs, {len(companies)} companies")
    print(f"  📍 Total locations in DB: {len(result_ids)}")
    
    return {
        'time': total_time,
        'egress_bytes': total_egress,
        'queries': ids_analysis['count'] + filters_analysis['count'] + pagination_analysis['count'],
        'filter_counts': {
            'auction_years': len(auction_years),
            'technologies': len(technologies), 
            'companies': len(companies)
        }
    }

def test_o3_suggested_approach():
    """Test O3's suggested approach with pre-computed filter options"""
    print("\n" + "="*70)
    print("🚀 TESTING O3 SUGGESTED APPROACH (Pre-computed filters)")
    print("="*70)
    
    reset_queries()
    start_time = time.time()
    
    # Pre-compute filter options once (O3 approach)
    print("1. Pre-computing ALL filter options (cached approach)...")
    reset_queries()
    
    with connection.cursor() as cursor:
        # Get all auction years
        cursor.execute("""
            SELECT DISTINCT jsonb_array_elements_text(auction_years::jsonb)
            FROM checker_locationgroup 
            WHERE auction_years IS NOT NULL
            ORDER BY 1 DESC
        """)
        all_auction_years = [row[0] for row in cursor.fetchall()]
        
        # Get all technologies  
        cursor.execute("""
            SELECT DISTINCT jsonb_object_keys(technologies::jsonb)
            FROM checker_locationgroup 
            WHERE technologies IS NOT NULL
            ORDER BY 1
        """)
        all_technologies = [row[0] for row in cursor.fetchall()]
        
        # Get all companies
        cursor.execute("""
            SELECT DISTINCT jsonb_object_keys(companies::jsonb)
            FROM checker_locationgroup 
            WHERE companies IS NOT NULL
            ORDER BY 1
        """)
        all_companies = [row[0] for row in cursor.fetchall()]
    
    filters_analysis = analyze_queries()
    auction_egress = estimate_egress_bytes(all_auction_years, "ALL Auction Years")
    tech_egress = estimate_egress_bytes(all_technologies, "ALL Technologies")
    company_egress = estimate_egress_bytes(all_companies, "ALL Companies")
    
    # Get paginated results (same as current approach)
    print("2. Getting paginated results only...")
    reset_queries()
    
    location_groups = LocationGroup.objects.all()
    optimized_locations = location_groups.only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    paginator = Paginator(optimized_locations, 25)
    page_obj = paginator.page(1)
    
    pagination_analysis = analyze_queries()
    page_data = list(page_obj)  # Force evaluation
    page_egress = estimate_egress_bytes([{
        'id': loc.id,
        'location': loc.location,
        'county': loc.county,
        'lat': loc.latitude,
        'lng': loc.longitude,
        'descriptions': loc.descriptions,
        'technologies': loc.technologies,
        'companies': loc.companies,
        'auction_years': loc.auction_years,
        'component_count': loc.component_count,
        'capacity': loc.normalized_capacity_mw
    } for loc in page_data], "Page Data (25 items)")
    
    total_time = time.time() - start_time
    total_egress = auction_egress + tech_egress + company_egress + page_egress
    
    print(f"\n📈 O3 APPROACH RESULTS:")
    print(f"  ⏱️  Total time: {total_time:.3f}s")
    print(f"  🗃️  Total queries: {filters_analysis['count'] + pagination_analysis['count']}")
    print(f"  📤 Total egress: {total_egress:,} bytes ({total_egress/1024:.1f} KB)")
    print(f"  📋 Filter counts: {len(all_auction_years)} years, {len(all_technologies)} techs, {len(all_companies)} companies")
    
    return {
        'time': total_time,
        'egress_bytes': total_egress,
        'queries': filters_analysis['count'] + pagination_analysis['count'],
        'filter_counts': {
            'auction_years': len(all_auction_years),
            'technologies': len(all_technologies),
            'companies': len(all_companies)
        }
    }

def test_search_map_approach():
    """Test current search-map approach (views_search_map_simple.py logic)"""
    print("\n" + "="*70)
    print("🗺️  TESTING CURRENT SEARCH-MAP APPROACH (views_search_map_simple.py)")
    print("="*70)
    
    reset_queries()
    start_time = time.time()
    
    # Simulate search-map sampling approach
    location_groups = LocationGroup.objects.all()
    total_locations = location_groups.count()
    
    print("1. Getting sample data for filter options...")
    reset_queries()
    
    if total_locations <= 1000:
        sample_size = total_locations
    else:
        sample_size = 1000
    
    sample_data = location_groups.values_list(
        'auction_years', 'technologies', 'companies'
    )[:sample_size]
    
    # Process sample data
    all_auction_years = set()
    all_technologies = set()
    all_companies = set()
    
    for years, techs, comps in sample_data:
        if years:
            all_auction_years.update(years)
        if techs:
            all_technologies.update(techs.keys())
        if comps:
            all_companies.update(comps.keys())
    
    auction_years = sorted(list(all_auction_years))
    technologies = sorted(list(all_technologies))
    companies = sorted(list(all_companies))
    
    sampling_analysis = analyze_queries()
    
    # Estimate egress for sample data
    sample_egress = estimate_egress_bytes(list(sample_data), f"Sample Data ({sample_size} rows)")
    auction_egress = estimate_egress_bytes(auction_years, "Auction Years from Sample")
    tech_egress = estimate_egress_bytes(technologies, "Technologies from Sample")
    company_egress = estimate_egress_bytes(companies, "Companies from Sample")
    
    # Get paginated results
    print("2. Getting paginated results...")
    reset_queries()
    
    optimized_locations = location_groups.only(
        'id', 'location', 'county', 'latitude', 'longitude',
        'descriptions', 'technologies', 'companies', 'auction_years',
        'component_count', 'normalized_capacity_mw'
    )
    
    paginator = Paginator(optimized_locations, 25)
    page_obj = paginator.page(1)
    
    pagination_analysis = analyze_queries()
    page_data = list(page_obj)
    page_egress = estimate_egress_bytes([{
        'id': loc.id,
        'location': loc.location,
        'county': loc.county,
        'lat': loc.latitude,
        'lng': loc.longitude,
        'descriptions': loc.descriptions,
        'technologies': loc.technologies,
        'companies': loc.companies,
        'auction_years': loc.auction_years,
        'component_count': loc.component_count,
        'capacity': loc.normalized_capacity_mw
    } for loc in page_data], "Page Data (25 items)")
    
    total_time = time.time() - start_time
    total_egress = sample_egress + auction_egress + tech_egress + company_egress + page_egress
    
    print(f"\n📈 SEARCH-MAP APPROACH RESULTS:")
    print(f"  ⏱️  Total time: {total_time:.3f}s")
    print(f"  🗃️  Total queries: {sampling_analysis['count'] + pagination_analysis['count']}")
    print(f"  📤 Total egress: {total_egress:,} bytes ({total_egress/1024:.1f} KB)")
    print(f"  📋 Filter counts: {len(auction_years)} years, {len(technologies)} techs, {len(companies)} companies")
    print(f"  📍 Sample size: {sample_size} locations")
    
    return {
        'time': total_time,
        'egress_bytes': total_egress,
        'queries': sampling_analysis['count'] + pagination_analysis['count'],
        'filter_counts': {
            'auction_years': len(auction_years),
            'technologies': len(technologies),
            'companies': len(companies)
        },
        'sample_size': sample_size
    }

def run_comparison():
    """Run all tests and compare results"""
    print("🧪 DEEP DIVE EGRESS ANALYSIS")
    print("Testing actual database queries and egress patterns")
    print("Challenging O3's assumptions with real measurements...")
    
    # Run all approaches
    current_results = test_current_search_approach()
    o3_results = test_o3_suggested_approach()
    searchmap_results = test_search_map_approach()
    
    # Print comparison
    print("\n" + "="*70)
    print("📊 COMPREHENSIVE COMPARISON")
    print("="*70)
    
    approaches = [
        ("Current Search", current_results),
        ("O3 Suggested", o3_results),
        ("Search-Map", searchmap_results)
    ]
    
    print(f"{'Approach':<15} {'Time(s)':<8} {'Queries':<8} {'Egress(KB)':<12} {'Years':<6} {'Techs':<6} {'Companies':<10}")
    print("-" * 80)
    
    for name, results in approaches:
        print(f"{name:<15} {results['time']:<8.3f} {results['queries']:<8} "
              f"{results['egress_bytes']/1024:<12.1f} "
              f"{results['filter_counts']['auction_years']:<6} "
              f"{results['filter_counts']['technologies']:<6} "
              f"{results['filter_counts']['companies']:<10}")
    
    # Analysis
    print(f"\n🔍 ANALYSIS:")
    print(f"  📤 Egress difference (Current vs O3): {(current_results['egress_bytes'] - o3_results['egress_bytes'])/1024:.1f} KB")
    print(f"  ⏱️  Time difference (Current vs O3): {(current_results['time'] - o3_results['time'])*1000:.1f} ms")
    print(f"  🗃️  Query difference (Current vs O3): {current_results['queries'] - o3_results['queries']} queries")
    
    # Determine if O3's assumptions hold
    egress_savings = current_results['egress_bytes'] - o3_results['egress_bytes']
    if egress_savings > 100 * 1024:  # More than 100KB savings
        print(f"\n✅ O3's assumptions VALIDATED: Significant egress savings ({egress_savings/1024:.1f} KB)")
    else:
        print(f"\n❌ O3's assumptions CHALLENGED: Minimal egress difference ({egress_savings/1024:.1f} KB)")
        print("     The real bottleneck may be elsewhere!")

if __name__ == "__main__":
    run_comparison()