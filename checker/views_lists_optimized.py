"""
Optimized list views for companies and technologies
Uses cached data and LocationGroup for high performance
"""
import logging
import time
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.core.cache import cache
import json

from .models import Component, LocationGroup
from .utils import normalize

logger = logging.getLogger(__name__)


def company_list_optimized(request):
    """
    Optimized company list view supporting multiple sort options
    """
    start_time = time.time()
    
    # Determine default sort based on URL path
    path = request.path
    if 'by-total-capacity' in path:
        default_sort = 'capacity'
    elif 'by-component-count' in path:
        default_sort = 'components'
    else:
        default_sort = 'capacity'
    
    # Get sort parameters
    sort_by = request.GET.get('sort_by', default_sort)  # capacity, components, locations
    sort_order = request.GET.get('sort_order', 'desc')
    page = int(request.GET.get('page', 1))
    per_page = 100
    
    # Try to get from cache first
    cache_key = f'company_list_{sort_by}_{sort_order}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        companies = json.loads(cached_data)
        logger.info(f"Company list loaded from cache in {time.time() - start_time:.2f}s")
    else:
        # EGRESS-OPTIMIZED: Use direct SQL aggregation instead of fetching all records
        logger.info("🔥 EGRESS-OPTIMIZED: Building company list using SQL aggregation")
        
        from django.db import connection
        
        # Use raw SQL to calculate company statistics efficiently
        # This avoids loading 16,009 records into memory
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    company_name,
                    COUNT(*) as location_count,
                    SUM(company_count) as component_count,
                    SUM(normalized_capacity_mw) as total_capacity
                FROM (
                    SELECT 
                        jsonb_object_keys(companies) as company_name,
                        (companies->jsonb_object_keys(companies))::int as company_count,
                        normalized_capacity_mw
                    FROM checker_locationgroup 
                    WHERE companies IS NOT NULL
                ) as company_data
                GROUP BY company_name
                ORDER BY total_capacity DESC
            """)
            
            companies = []
            for row in cursor.fetchall():
                companies.append({
                    'company_name': row[0],
                    'company_id': normalize(row[0]),
                    'location_count': row[1],
                    'component_count': row[2],
                    'total_capacity': float(row[3] or 0)
                })
        
        # Sort by requested criteria
        if sort_by == 'name':
            reverse = (sort_order == 'desc')
            companies.sort(key=lambda x: x['company_name'].lower(), reverse=reverse)
        elif sort_by == 'locations':
            reverse = (sort_order == 'desc')
            companies.sort(key=lambda x: x['location_count'], reverse=reverse)
        elif sort_by == 'components':
            reverse = (sort_order == 'desc')
            companies.sort(key=lambda x: x['component_count'], reverse=reverse)
        else:  # capacity (default)
            reverse = (sort_order == 'desc')
            companies.sort(key=lambda x: x['total_capacity'], reverse=reverse)
        
        # Cache for 1 hour
        cache.set(cache_key, json.dumps(companies[:500]), timeout=3600)
    
    # EGRESS-OPTIMIZED: Location counts already calculated from LocationGroup aggregation
    paginator = Paginator(companies, per_page)
    page_obj = paginator.get_page(page)
    
    # No need to recalculate location counts - already computed efficiently above!
    
    load_time = time.time() - start_time
    
    # MONITORING: Log optimization metrics
    # SQL aggregation approach: minimal rows processed (only final aggregated results)
    rows_processed = len(companies)  # Only the final aggregated company records
    estimated_old_bytes = 16009 * 22 * 50  # Old: all LocationGroup fields fetched  
    estimated_new_bytes = rows_processed * 4 * 50  # New: only 4 aggregated fields per company
    reduction = ((estimated_old_bytes - estimated_new_bytes) / max(estimated_old_bytes, 1)) * 100
    
    logger.info(f"🔥 EGRESS-OPTIMIZED company list (sort={sort_by}):")
    logger.info(f"   📊 Companies found: {len(companies)}")
    logger.info(f"   📋 Displayed: {len(page_obj)} (page {page})")
    logger.info(f"   📦 Rows processed: {rows_processed} (SQL aggregated)")
    logger.info(f"   📊 Estimated egress: {estimated_new_bytes:,} bytes ({estimated_new_bytes/1024:.1f} KB)")
    logger.info(f"   💡 Estimated reduction: {reduction:.1f}% ({estimated_old_bytes:,} → {estimated_new_bytes:,} bytes)")
    logger.info(f"   ⏱️  Load time: {load_time:.3f}s")
    
    # Generate chart data for company distribution pie chart
    # Get top 15 companies for the chart to keep it readable
    chart_companies = companies[:15] if len(companies) > 15 else companies
    
    # Prepare chart data - component count
    company_chart_labels = [comp['company_name'] for comp in chart_companies]
    company_chart_values = [comp['component_count'] for comp in chart_companies]
    
    # Prepare chart data - capacity
    company_capacity_chart_labels = [comp['company_name'] for comp in chart_companies]
    company_capacity_chart_values = [comp['total_capacity'] for comp in chart_companies]
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'total_companies': len(companies),
        'load_time': load_time,
        # Chart data
        'company_chart_labels': company_chart_labels,
        'company_chart_values': company_chart_values,
        'company_capacity_chart_labels': company_capacity_chart_labels,
        'company_capacity_chart_values': company_capacity_chart_values,
    }
    
    return render(request, 'checker/company_list_optimized.html', context)


def technology_list_optimized(request):
    """
    Optimized technology list view supporting multiple sort options
    """
    start_time = time.time()
    
    # Determine default sort based on URL path
    path = request.path
    if 'by-total-capacity' in path:
        default_sort = 'capacity'
    else:
        default_sort = 'capacity'
    
    # Get sort parameters
    sort_by = request.GET.get('sort_by', default_sort)  # capacity, components, locations
    sort_order = request.GET.get('sort_order', 'desc')
    page = int(request.GET.get('page', 1))
    per_page = 100
    
    # Try to get from cache first (v3: individual + grouped interconnectors)
    cache_key = f'technology_list_v3_{sort_by}_{sort_order}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        technologies = json.loads(cached_data)
        logger.info(f"Technology list loaded from cache in {time.time() - start_time:.2f}s")
    else:
        # Build technology list from database using SQL aggregation (MUCH more efficient)
        logger.info("Building technology list from database...")
        
        # EGRESS-OPTIMIZED: Use direct SQL aggregation instead of fetching all records
        logger.info("🔥 EGRESS-OPTIMIZED: Building technology list using SQL aggregation")
        
        from django.db import connection
        
        # Use raw SQL to calculate technology statistics efficiently
        # This avoids loading 16,009 records into memory
        with connection.cursor() as cursor:
            cursor.execute("""
                -- Get both individual technologies AND grouped interconnector
                WITH individual_techs AS (
                    SELECT 
                        tech_name,
                        COUNT(*) as location_count,
                        SUM(tech_count) as component_count,
                        SUM(normalized_capacity_mw) as total_capacity
                    FROM (
                        SELECT 
                            jsonb_object_keys(technologies) as tech_name,
                            (technologies->jsonb_object_keys(technologies))::int as tech_count,
                            normalized_capacity_mw
                        FROM checker_locationgroup 
                        WHERE technologies IS NOT NULL
                    ) as tech_data
                    GROUP BY tech_name
                ),
                grouped_interconnector AS (
                    SELECT 
                        'Interconnector' as tech_name,
                        SUM(location_count) as location_count,
                        SUM(component_count) as component_count,
                        SUM(total_capacity) as total_capacity
                    FROM individual_techs
                    WHERE tech_name IN (
                        'BritNED (Netherlands)', 'Eleclink (France)', 'EWIC (Ireland)', 
                        'EWIC (Republic of Ireland)', 'Greenlink (Republic of Ireland)',
                        'IFA2 (France)', 'IFA (France)', 'Moyle (Northern Ireland)',
                        'NEMO (Belgium)', 'NeuConnect (Germany)', 'NSL (Norway)', 'VikingLink (Denmark)'
                    )
                )
                SELECT tech_name, location_count, component_count, total_capacity
                FROM individual_techs
                UNION ALL
                SELECT tech_name, location_count, component_count, total_capacity
                FROM grouped_interconnector
                ORDER BY total_capacity DESC
            """)
            
            technologies = []
            for row in cursor.fetchall():
                technologies.append({
                    'technology': row[0],
                    'location_count': int(row[1] or 0),
                    'component_count': int(row[2] or 0),
                    'total_capacity': float(row[3] or 0)
                })
        
        # Sort by requested criteria
        if sort_by == 'locations':
            reverse = (sort_order == 'desc')
            technologies.sort(key=lambda x: x['location_count'], reverse=reverse)
        elif sort_by == 'components':
            reverse = (sort_order == 'desc')
            technologies.sort(key=lambda x: x['component_count'], reverse=reverse)
        else:  # capacity (default)
            reverse = (sort_order == 'desc')
            technologies.sort(key=lambda x: x['total_capacity'], reverse=reverse)
        
        # Cache for 1 hour
        cache.set(cache_key, json.dumps(technologies[:200]), timeout=3600)
    
    # EGRESS-OPTIMIZED: Location counts already calculated from LocationGroup aggregation
    paginator = Paginator(technologies, per_page)
    page_obj = paginator.get_page(page)
    
    # No need to recalculate location counts - already computed efficiently above!
    
    # Generate chart data for technology distribution pie chart
    # Get top 15 technologies for the chart to keep it readable
    chart_technologies = technologies[:15] if len(technologies) > 15 else technologies
    
    # Prepare chart data - component count
    tech_chart_labels = [tech['technology'] for tech in chart_technologies]
    tech_chart_values = [tech['component_count'] for tech in chart_technologies]
    
    # Prepare chart data - capacity
    tech_capacity_chart_labels = [tech['technology'] for tech in chart_technologies]
    tech_capacity_chart_values = [tech['total_capacity'] for tech in chart_technologies]
    
    load_time = time.time() - start_time
    
    # MONITORING: Log optimization metrics
    # SQL aggregation approach: minimal rows processed (only final aggregated results)
    rows_processed = len(technologies)  # Only the final aggregated technology records
    estimated_old_bytes = 16009 * 22 * 50  # Old: all LocationGroup fields fetched  
    estimated_new_bytes = rows_processed * 4 * 50  # New: only 4 aggregated fields per tech
    reduction = ((estimated_old_bytes - estimated_new_bytes) / max(estimated_old_bytes, 1)) * 100
    
    logger.info(f"🔥 EGRESS-OPTIMIZED technology list (sort={sort_by}):")
    logger.info(f"   📊 Technologies found: {len(technologies)}")
    logger.info(f"   📋 Displayed: {len(page_obj)} (page {page})")
    logger.info(f"   📦 Rows processed: {rows_processed} (SQL aggregated)")
    logger.info(f"   📊 Estimated egress: {estimated_new_bytes:,} bytes ({estimated_new_bytes/1024:.1f} KB)")
    logger.info(f"   💡 Estimated reduction: {reduction:.1f}% ({estimated_old_bytes:,} → {estimated_new_bytes:,} bytes)")
    logger.info(f"   ⏱️  Load time: {load_time:.3f}s")
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'total_technologies': len(technologies),
        'load_time': load_time,
        # Chart data
        'tech_chart_labels': tech_chart_labels,
        'tech_chart_values': tech_chart_values,
        'tech_capacity_chart_labels': tech_capacity_chart_labels,
        'tech_capacity_chart_values': tech_capacity_chart_values,
    }
    
    return render(request, 'checker/technology_list_optimized.html', context)