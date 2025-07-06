"""
Real-time monitoring dashboard for egress tracking
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from .egress_monitor import monitor
import json
from datetime import datetime, timedelta

def monitoring_dashboard(request):
    """Main monitoring dashboard view"""
    context = {
        'title': 'Egress Monitoring Dashboard',
        'refresh_interval': 30  # seconds
    }
    return render(request, 'monitoring/dashboard.html', context)


def monitoring_api(request):
    """API endpoint for real-time monitoring data"""
    # Get current summary
    summary = monitor.get_summary()
    
    # Get recent API calls
    recent_calls = []
    for i in range(10):  # Last 10 minutes
        timestamp = int(timezone.now().timestamp()) - (i * 60)
        cache_key = f"egress_monitor:api_calls:{timestamp}"
        calls = cache.get(cache_key, [])
        recent_calls.extend(calls)
    
    # Get recent alerts
    recent_alerts = []
    for i in range(60):  # Last hour
        timestamp = int(timezone.now().timestamp()) - (i * 60)
        cache_key = f"egress_monitor:alerts:{timestamp}"
        alerts = cache.get(cache_key, [])
        recent_alerts.extend(alerts)
    
    # Calculate rates
    runtime_hours = summary['runtime_seconds'] / 3600
    
    egress_rates = {
        'supabase_mb_per_hour': summary['supabase']['total_mb_received'] / runtime_hours if runtime_hours > 0 else 0,
        'redis_mb_per_hour': (summary['redis']['total_mb_sent'] + summary['redis']['total_mb_received']) / runtime_hours if runtime_hours > 0 else 0,
        'total_network_mb_per_hour': summary['heroku']['network_mb_sent'] / runtime_hours if runtime_hours > 0 else 0
    }
    
    # Estimate monthly usage
    monthly_estimates = {
        'supabase_gb_monthly': egress_rates['supabase_mb_per_hour'] * 24 * 30 / 1024,
        'total_network_gb_monthly': egress_rates['total_network_mb_per_hour'] * 24 * 30 / 1024
    }
    
    response_data = {
        'summary': summary,
        'rates': egress_rates,
        'monthly_estimates': monthly_estimates,
        'recent_calls': recent_calls[-20:],  # Last 20 calls
        'recent_alerts': recent_alerts[-10:],  # Last 10 alerts
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(response_data)


def endpoint_analysis(request):
    """Detailed analysis of specific endpoints"""
    endpoint = request.GET.get('endpoint', '')
    
    if not endpoint:
        return JsonResponse({'error': 'No endpoint specified'})
    
    # Get historical data for this endpoint
    historical_data = []
    for i in range(24):  # Last 24 hours
        timestamp = int(timezone.now().timestamp()) - (i * 3600)
        cache_key = f"egress_monitor:endpoint:{endpoint}:{timestamp}"
        data = cache.get(cache_key, {})
        if data:
            historical_data.append(data)
    
    # Calculate statistics
    if historical_data:
        total_calls = sum(d.get('count', 0) for d in historical_data)
        total_mb = sum(d.get('total_mb', 0) for d in historical_data)
        avg_response_size = sum(d.get('avg_response_kb', 0) for d in historical_data) / len(historical_data)
    else:
        total_calls = 0
        total_mb = 0
        avg_response_size = 0
    
    analysis = {
        'endpoint': endpoint,
        'last_24h': {
            'total_calls': total_calls,
            'total_mb': total_mb,
            'avg_response_kb': avg_response_size,
            'calls_per_hour': total_calls / 24
        },
        'historical_data': historical_data,
        'recommendations': get_endpoint_recommendations(endpoint, total_mb, total_calls)
    }
    
    return JsonResponse(analysis)


def get_endpoint_recommendations(endpoint, total_mb, total_calls):
    """Get optimization recommendations for an endpoint"""
    recommendations = []
    
    # High egress endpoints
    if total_mb > 100:  # More than 100MB in 24h
        recommendations.append({
            'type': 'warning',
            'message': f'High data transfer: {total_mb:.2f}MB in 24h',
            'action': 'Consider adding caching or reducing response size'
        })
    
    # High frequency endpoints
    if total_calls > 1000:  # More than 1000 calls in 24h
        recommendations.append({
            'type': 'info',
            'message': f'High call frequency: {total_calls} calls in 24h',
            'action': 'Consider implementing rate limiting or caching'
        })
    
    # Specific endpoint recommendations
    if '/api/map-data/' in endpoint:
        recommendations.append({
            'type': 'tip',
            'message': 'Map data endpoint detected',
            'action': 'Ensure proper bounds checking and limit feature count'
        })
    
    if '/api/search-geojson/' in endpoint:
        recommendations.append({
            'type': 'tip',
            'message': 'Search GeoJSON endpoint detected',
            'action': 'Consider pagination and result limiting'
        })
    
    return recommendations


def export_monitoring_data(request):
    """Export monitoring data as CSV/JSON"""
    format_type = request.GET.get('format', 'json')
    
    # Get all cached monitoring data
    all_data = {
        'summary': monitor.get_summary(),
        'export_timestamp': timezone.now().isoformat(),
        'runtime_seconds': monitor.get_summary()['runtime_seconds']
    }
    
    if format_type == 'csv':
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="egress_monitoring.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value', 'Unit'])
        
        summary = all_data['summary']
        writer.writerow(['Runtime', summary['runtime_seconds'], 'seconds'])
        writer.writerow(['Supabase Queries', summary['supabase']['total_queries'], 'count'])
        writer.writerow(['Supabase Data', summary['supabase']['total_mb_received'], 'MB'])
        writer.writerow(['Redis Commands', summary['redis']['total_commands'], 'count'])
        writer.writerow(['Redis Hit Rate', summary['redis']['cache_hit_rate'], '%'])
        writer.writerow(['Memory Usage', summary['heroku']['memory_usage_percent'], '%'])
        writer.writerow(['CPU Usage', summary['heroku']['cpu_percent'], '%'])
        
        return response
    else:
        return JsonResponse(all_data, json_dumps_params={'indent': 2})


def reset_monitoring(request):
    """Reset monitoring counters"""
    if request.method == 'POST':
        global monitor
        from .egress_monitor import EgressMonitor
        monitor = EgressMonitor()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Monitoring counters reset',
            'timestamp': timezone.now().isoformat()
        })
    
    return JsonResponse({'error': 'POST method required'})