"""
Simple egress monitoring for immediate use
"""
import time
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Simple in-memory storage
monitoring_data = {
    'api_calls': [],
    'large_responses': [],
    'start_time': time.time(),
    'total_bytes': 0,
    'endpoint_stats': {}
}

@require_http_methods(["GET"])
def simple_dashboard(request):
    """Simple monitoring dashboard"""
    return render(request, 'monitoring/simple_dashboard.html')

@require_http_methods(["GET"]) 
def simple_api(request):
    """Get monitoring data"""
    runtime = time.time() - monitoring_data['start_time']
    
    # Calculate stats
    total_mb = monitoring_data['total_bytes'] / 1024 / 1024
    calls_per_min = len(monitoring_data['api_calls']) / (runtime / 60) if runtime > 0 else 0
    
    # Monthly projection
    hours_elapsed = runtime / 3600
    if hours_elapsed > 0:
        mb_per_hour = total_mb / hours_elapsed
        monthly_gb = mb_per_hour * 24 * 30 / 1024
    else:
        monthly_gb = 0
    
    # Top endpoints
    top_endpoints = sorted(
        monitoring_data['endpoint_stats'].items(),
        key=lambda x: x[1]['bytes'],
        reverse=True
    )[:10]
    
    # Calculate memory statistics
    recent_calls_with_memory = [call for call in monitoring_data['api_calls'][-100:] if 'memory_rss_mb' in call]
    if recent_calls_with_memory:
        current_memory_mb = recent_calls_with_memory[-1]['memory_rss_mb']
        max_memory_mb = max(call['memory_rss_mb'] for call in recent_calls_with_memory)
        avg_memory_delta = sum(call.get('memory_delta_mb', 0) for call in recent_calls_with_memory) / len(recent_calls_with_memory)
    else:
        current_memory_mb = 0
        max_memory_mb = 0
        avg_memory_delta = 0

    return JsonResponse({
        'runtime_seconds': runtime,
        'total_api_calls': len(monitoring_data['api_calls']),
        'total_mb': round(total_mb, 2),
        'calls_per_minute': round(calls_per_min, 2),
        'monthly_gb_estimate': round(monthly_gb, 2),
        'supabase_limit_percent': round((monthly_gb / 5) * 100, 1),
        'memory_stats': {
            'current_memory_mb': round(current_memory_mb, 1),
            'max_memory_mb': round(max_memory_mb, 1),
            'avg_memory_delta_mb': round(avg_memory_delta, 2)
        },
        'large_responses': monitoring_data['large_responses'][-10:],
        'memory_alerts': monitoring_data.get('memory_alerts', [])[-10:],
        'top_endpoints': [
            {
                'endpoint': endpoint,
                'calls': stats['calls'],
                'total_mb': round(stats['bytes'] / 1024 / 1024, 2)
            }
            for endpoint, stats in top_endpoints
        ],
        'recent_calls': monitoring_data['api_calls'][-20:]
    })

def log_api_call(endpoint, method='GET', response_size=0, duration=0, memory_delta_mb=0, memory_rss_mb=0):
    """Log an API call with enhanced metrics"""
    monitoring_data['api_calls'].append({
        'endpoint': endpoint,
        'method': method,
        'size': response_size,
        'duration': duration,
        'memory_delta_mb': round(memory_delta_mb, 2),
        'memory_rss_mb': round(memory_rss_mb, 1),
        'timestamp': time.time()
    })
    
    # Update total
    monitoring_data['total_bytes'] += response_size
    
    # Update endpoint stats
    if endpoint not in monitoring_data['endpoint_stats']:
        monitoring_data['endpoint_stats'][endpoint] = {
            'calls': 0,
            'bytes': 0
        }
    monitoring_data['endpoint_stats'][endpoint]['calls'] += 1
    monitoring_data['endpoint_stats'][endpoint]['bytes'] += response_size
    
    # Check for large responses
    if response_size > 5 * 1024 * 1024:  # 5MB
        monitoring_data['large_responses'].append({
            'endpoint': endpoint,
            'size_mb': round(response_size / 1024 / 1024, 2),
            'timestamp': time.time()
        })
    
    # Check for memory alerts
    if memory_delta_mb > 50:  # 50MB memory increase
        if 'memory_alerts' not in monitoring_data:
            monitoring_data['memory_alerts'] = []
        monitoring_data['memory_alerts'].append({
            'endpoint': endpoint,
            'memory_delta_mb': round(memory_delta_mb, 2),
            'memory_rss_mb': round(memory_rss_mb, 1),
            'timestamp': time.time()
        })
        
        # Keep memory alerts manageable
        if len(monitoring_data['memory_alerts']) > 50:
            monitoring_data['memory_alerts'] = monitoring_data['memory_alerts'][-25:]
    
    # Keep lists manageable
    if len(monitoring_data['api_calls']) > 1000:
        monitoring_data['api_calls'] = monitoring_data['api_calls'][-500:]
    if len(monitoring_data['large_responses']) > 100:
        monitoring_data['large_responses'] = monitoring_data['large_responses'][-50:]