from django.shortcuts import render, redirect
from django.core.cache import cache
from django.db.models import Count, Sum, Q
from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required
from checker.models import Component
import json
import logging

logger = logging.getLogger(__name__)


@staff_member_required
def statistics_view_optimized(request):
    """Optimized statistics view that uses cached data"""
    
    # Check if we should force rebuild
    rebuild = request.GET.get('rebuild', '').lower() == 'true'
    
    # Try to get cached data first
    cache_key = 'statistics_page_data'
    cached_data = None
    
    if not rebuild:
        cached_json = cache.get(cache_key)
        if cached_json:
            try:
                cached_data = json.loads(cached_json)
                logger.info("Statistics loaded from cache")
            except:
                logger.error("Failed to parse cached statistics data")
    
    # If no cached data, calculate it (this is the slow part)
    if not cached_data:
        logger.info("Building statistics from database...")
        
        # For immediate response, redirect to a loading page
        if not rebuild and request.GET.get('loading') != 'true':
            # Start building cache in background
            from django.core.management import call_command
            from threading import Thread
            
            def build_cache():
                try:
                    call_command('build_statistics_cache')
                except Exception as e:
                    logger.error(f"Failed to build statistics cache: {e}")
            
            Thread(target=build_cache).start()
            
            # Redirect to loading page
            return render(request, 'checker/statistics_loading.html')
        
        # If we're here, we need to calculate stats synchronously
        stats_data = {}
        
        # Calculate all statistics (same as management command)
        stats_data['summary'] = {
            'total_components': Component.objects.count(),
            'total_companies': Component.objects.exclude(
                Q(company_name__isnull=True) | Q(company_name='')
            ).values('company_name').distinct().count(),
            'total_technologies': Component.objects.values('technology').distinct().count(),
            'total_capacity': float(
                Component.objects.aggregate(
                    total=Sum('derated_capacity_mw')
                )['total'] or 0
            )
        }
        
        # Use the calculated data
        cached_data = stats_data
    
    # Get summary data
    summary = cached_data.get('summary', {})
    total_components = summary.get('total_components', 0)
    
    # Get data with percentage calculations
    top_companies_data = cached_data.get('top_companies_count', [])[:25]
    tech_distribution = cached_data.get('tech_by_count', [])[:25]
    year_distribution = cached_data.get('components_by_year', [])
    top_derated_components = cached_data.get('top_components_capacity', [])[:20]
    
    # Add percentages and company_id to company data
    from .utils import normalize
    for company in top_companies_data:
        company['company_id'] = normalize(company['company_name'])
        if total_components > 0:
            company['percentage'] = (company['count'] / total_components) * 100
        else:
            company['percentage'] = 0
            
    # Add percentages to tech data
    for tech in tech_distribution:
        if total_components > 0:
            tech['percentage'] = (tech['count'] / total_components) * 100
        else:
            tech['percentage'] = 0
            
    # Add percentages to year data
    for year in year_distribution:
        if total_components > 0:
            year['percentage'] = (year['count'] / total_components) * 100
        else:
            year['percentage'] = 0
    
    # Rename capacity field in top components to match template
    for comp in top_derated_components:
        if 'derated_capacity_mw' in comp:
            comp['derated_capacity'] = comp['derated_capacity_mw']
    
    # Prepare chart data for pie charts
    CHART_LIMIT = 10
    
    # Company chart data by count
    company_count_chart_labels = [c['company_name'] for c in top_companies_data[:CHART_LIMIT]]
    company_count_chart_values = [c['count'] for c in top_companies_data[:CHART_LIMIT]]
    # Add 'Other' if there are more companies
    if len(top_companies_data) > CHART_LIMIT:
        other_count = sum(c['count'] for c in top_companies_data[CHART_LIMIT:])
        company_count_chart_labels.append('Other')
        company_count_chart_values.append(other_count)
    
    # Company chart data by capacity (using cached capacity data if available)
    company_capacity_data = cached_data.get('top_companies_capacity', [])[:25]
    company_capacity_chart_labels = [c['company_name'] for c in company_capacity_data[:CHART_LIMIT]]
    company_capacity_chart_values = [float(c['total_capacity']) for c in company_capacity_data[:CHART_LIMIT]]
    if len(company_capacity_data) > CHART_LIMIT:
        other_capacity = sum(float(c['total_capacity']) for c in company_capacity_data[CHART_LIMIT:])
        company_capacity_chart_labels.append('Other')
        company_capacity_chart_values.append(other_capacity)
    
    # Technology chart data by count
    tech_chart_labels = [t['technology'] for t in tech_distribution[:CHART_LIMIT]]
    tech_chart_values = [t['count'] for t in tech_distribution[:CHART_LIMIT]]
    if len(tech_distribution) > CHART_LIMIT:
        other_tech_count = sum(t['count'] for t in tech_distribution[CHART_LIMIT:])
        tech_chart_labels.append('Other')
        tech_chart_values.append(other_tech_count)
    
    # Technology chart data by capacity
    tech_capacity_data = cached_data.get('tech_by_capacity', [])[:25]
    tech_capacity_chart_labels = [t['technology'] for t in tech_capacity_data[:CHART_LIMIT]]
    tech_capacity_chart_values = [float(t['total_capacity']) for t in tech_capacity_data[:CHART_LIMIT]]
    if len(tech_capacity_data) > CHART_LIMIT:
        other_tech_capacity = sum(float(t['total_capacity']) for t in tech_capacity_data[CHART_LIMIT:])
        tech_capacity_chart_labels.append('Other')
        tech_capacity_chart_values.append(other_tech_capacity)
    
    # Prepare context for template with variable names matching the template
    context = {
        # Summary stats
        'total_components': total_components,
        'total_companies': summary.get('total_companies', 0), 
        'total_cmus': Component.objects.values('cmu_id').distinct().count(),  # Not cached, small query
        'total_unique_locations': Component.objects.exclude(location__isnull=True).exclude(location='').values('location').distinct().count(),  # Not cached, but reasonable
        
        # Company data
        'top_companies_data': top_companies_data,
        
        # Technology data  
        'tech_distribution': tech_distribution,
        
        # Year distribution
        'year_distribution': year_distribution,
        
        # Top components
        'top_derated_components': top_derated_components,
        
        # Request parameters for UI
        'company_sort': 'count',
        'company_order': 'desc', 
        'tech_sort': 'count',
        'tech_order': 'desc',
        'show_all_techs': False,
        
        # Chart data
        'company_count_chart_labels': company_count_chart_labels,
        'company_count_chart_values': company_count_chart_values,
        'company_capacity_chart_labels': company_capacity_chart_labels,
        'company_capacity_chart_values': company_capacity_chart_values,
        'tech_chart_labels': tech_chart_labels,
        'tech_chart_values': tech_chart_values,
        'tech_capacity_chart_labels': tech_capacity_chart_labels,
        'tech_capacity_chart_values': tech_capacity_chart_values,
        
        # Cache status
        'cached': bool(cached_data),
    }
    
    # Add monitoring data for admin dashboard
    if request.user.is_staff:
        # Get monitoring data
        from django.utils import timezone
        from datetime import timedelta
        import redis
        from django.conf import settings
        
        try:
            # Redis status
            redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
            redis_info = redis_client.info('memory')
            redis_memory_mb = redis_info.get('used_memory', 0) / (1024 * 1024)
            context['redis_memory_usage'] = f"{redis_memory_mb:.1f} MB"
        except:
            context['redis_memory_usage'] = "Connection Error"
        
        # Cache status
        context['cache_status'] = bool(cached_data)
        
        # Last crawl date (you can customize this based on your crawl tracking)
        try:
            latest_component = Component.objects.order_by('-id').first()
            if latest_component:
                # Assuming newest components are from latest crawl
                context['last_crawl_date'] = latest_component.id  # You might want to add a created_at field
        except:
            pass
        
        # Database last updated
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # This is PostgreSQL specific - adjust for your database
                cursor.execute("""
                    SELECT MAX(last_value) 
                    FROM (
                        SELECT last_value FROM checker_component_id_seq
                    ) as seq
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    context['last_db_update'] = f"{result[0]:,} records"
        except:
            pass
        
        # Active users and searches (placeholder - implement based on your tracking)
        context['active_users_24h'] = "Feature coming soon"
        context['searches_24h'] = "Feature coming soon"
        
        # Use admin template
        return render(request, 'checker/statistics_admin.html', context)
    
    return render(request, 'checker/statistics.html', context)


def statistics_sections_view(request):
    """New view that loads statistics in sections for better UX"""
    section = request.GET.get('section', 'summary')
    
    # This could be AJAX-powered for dynamic loading
    if section == 'summary':
        # Just load summary stats
        context = {
            'summary': {
                'total_components': Component.objects.count(),
                'total_companies': Component.objects.exclude(
                    Q(company_name__isnull=True) | Q(company_name='')
                ).values('company_name').distinct().count(),
                'total_technologies': Component.objects.values('technology').distinct().count(),
                'total_capacity': float(
                    Component.objects.aggregate(
                        total=Sum('derated_capacity_mw')
                    )['total'] or 0
                )
            }
        }
        return render(request, 'checker/statistics_summary.html', context)
    
    elif section == 'companies':
        # Load company statistics
        sort_by = request.GET.get('sort', 'count')
        # TODO: implement company stats
        pass
        
    elif section == 'technologies':
        # Load technology statistics
        # TODO: implement tech stats
        pass
        
    # Default fallback
    return render(request, 'checker/statistics.html', {})