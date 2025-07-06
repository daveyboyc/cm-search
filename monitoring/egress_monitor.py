"""
Comprehensive Egress Monitoring System
Tracks data transfer across Supabase, Redis, and Heroku
"""
import time
import json
import logging
import functools
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
import redis
import psutil
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('egress_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('egress_monitor')

class EgressMonitor:
    """Monitor data egress across all services"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            'supabase': {
                'queries': 0,
                'bytes_sent': 0,
                'bytes_received': 0,
                'api_calls': {}
            },
            'redis': {
                'commands': 0,
                'bytes_sent': 0,
                'bytes_received': 0,
                'cache_hits': 0,
                'cache_misses': 0
            },
            'heroku': {
                'memory_usage': 0,
                'cpu_percent': 0,
                'network_bytes_sent': 0,
                'network_bytes_recv': 0
            },
            'api_endpoints': {}
        }
        
        # Track network stats at start
        if hasattr(psutil, 'net_io_counters'):
            net_io = psutil.net_io_counters()
            self.start_bytes_sent = net_io.bytes_sent
            self.start_bytes_recv = net_io.bytes_recv
    
    def log_supabase_query(self, query, params=None, response_size=0, duration=0):
        """Log Supabase database query"""
        self.metrics['supabase']['queries'] += 1
        self.metrics['supabase']['bytes_received'] += response_size
        
        logger.info(f"Supabase Query: {query[:100]}... | Size: {response_size} bytes | Duration: {duration}ms")
        
        # Save to cache for dashboard
        cache_key = f"egress_monitor:supabase:{int(time.time())}"
        cache.set(cache_key, {
            'query': query,
            'size': response_size,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }, timeout=3600)  # Keep for 1 hour
    
    def log_api_call(self, endpoint, method='GET', request_size=0, response_size=0, duration=0):
        """Log API endpoint calls"""
        key = f"{method} {endpoint}"
        
        if key not in self.metrics['api_endpoints']:
            self.metrics['api_endpoints'][key] = {
                'count': 0,
                'total_request_bytes': 0,
                'total_response_bytes': 0,
                'avg_duration': 0
            }
        
        endpoint_metrics = self.metrics['api_endpoints'][key]
        endpoint_metrics['count'] += 1
        endpoint_metrics['total_request_bytes'] += request_size
        endpoint_metrics['total_response_bytes'] += response_size
        
        # Update average duration
        prev_avg = endpoint_metrics['avg_duration']
        endpoint_metrics['avg_duration'] = (prev_avg * (endpoint_metrics['count'] - 1) + duration) / endpoint_metrics['count']
        
        logger.info(f"API Call: {key} | Req: {request_size} bytes | Resp: {response_size} bytes | Duration: {duration}ms")
        
        # Alert if response is large
        if response_size > 1024 * 1024:  # 1MB
            logger.warning(f"Large response detected: {key} returned {response_size / 1024 / 1024:.2f}MB")
    
    def log_redis_command(self, command, args=None, response_size=0):
        """Log Redis command"""
        self.metrics['redis']['commands'] += 1
        self.metrics['redis']['bytes_received'] += response_size
        
        # Estimate sent bytes (command + args)
        sent_bytes = len(command) + sum(len(str(arg)) for arg in (args or []))
        self.metrics['redis']['bytes_sent'] += sent_bytes
        
        logger.debug(f"Redis: {command} | Sent: {sent_bytes} bytes | Received: {response_size} bytes")
    
    def log_cache_hit(self, key, size=0):
        """Log cache hit"""
        self.metrics['redis']['cache_hits'] += 1
        logger.debug(f"Cache HIT: {key} | Size: {size} bytes")
    
    def log_cache_miss(self, key):
        """Log cache miss"""
        self.metrics['redis']['cache_misses'] += 1
        logger.debug(f"Cache MISS: {key}")
    
    def update_system_metrics(self):
        """Update system metrics (Heroku dyno stats)"""
        try:
            # Memory usage
            self.metrics['heroku']['memory_usage'] = psutil.virtual_memory().percent
            
            # CPU usage
            self.metrics['heroku']['cpu_percent'] = psutil.cpu_percent(interval=1)
            
            # Network I/O
            if hasattr(psutil, 'net_io_counters'):
                net_io = psutil.net_io_counters()
                self.metrics['heroku']['network_bytes_sent'] = net_io.bytes_sent - self.start_bytes_sent
                self.metrics['heroku']['network_bytes_recv'] = net_io.bytes_recv - self.start_bytes_recv
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def get_summary(self):
        """Get current metrics summary"""
        self.update_system_metrics()
        
        runtime = time.time() - self.start_time
        
        summary = {
            'runtime_seconds': runtime,
            'supabase': {
                'total_queries': self.metrics['supabase']['queries'],
                'total_mb_received': self.metrics['supabase']['bytes_received'] / 1024 / 1024,
                'queries_per_minute': self.metrics['supabase']['queries'] / (runtime / 60) if runtime > 0 else 0
            },
            'redis': {
                'total_commands': self.metrics['redis']['commands'],
                'total_mb_sent': self.metrics['redis']['bytes_sent'] / 1024 / 1024,
                'total_mb_received': self.metrics['redis']['bytes_received'] / 1024 / 1024,
                'cache_hit_rate': self.metrics['redis']['cache_hits'] / (self.metrics['redis']['cache_hits'] + self.metrics['redis']['cache_misses']) * 100 if (self.metrics['redis']['cache_hits'] + self.metrics['redis']['cache_misses']) > 0 else 0
            },
            'heroku': {
                'memory_usage_percent': self.metrics['heroku']['memory_usage'],
                'cpu_percent': self.metrics['heroku']['cpu_percent'],
                'network_mb_sent': self.metrics['heroku']['network_bytes_sent'] / 1024 / 1024,
                'network_mb_recv': self.metrics['heroku']['network_bytes_recv'] / 1024 / 1024
            },
            'top_endpoints': sorted(
                [
                    {
                        'endpoint': k,
                        'count': v['count'],
                        'total_mb': v['total_response_bytes'] / 1024 / 1024,
                        'avg_response_kb': v['total_response_bytes'] / v['count'] / 1024 if v['count'] > 0 else 0
                    }
                    for k, v in self.metrics['api_endpoints'].items()
                ],
                key=lambda x: x['total_mb'],
                reverse=True
            )[:10]
        }
        
        return summary
    
    def print_summary(self):
        """Print formatted summary"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("EGRESS MONITORING SUMMARY")
        print("="*60)
        print(f"Runtime: {summary['runtime_seconds']:.2f} seconds")
        
        print("\n📊 SUPABASE:")
        print(f"  Total Queries: {summary['supabase']['total_queries']}")
        print(f"  Data Received: {summary['supabase']['total_mb_received']:.2f} MB")
        print(f"  Query Rate: {summary['supabase']['queries_per_minute']:.2f} queries/min")
        
        print("\n💾 REDIS:")
        print(f"  Total Commands: {summary['redis']['total_commands']}")
        print(f"  Data Sent: {summary['redis']['total_mb_sent']:.2f} MB")
        print(f"  Data Received: {summary['redis']['total_mb_received']:.2f} MB")
        print(f"  Cache Hit Rate: {summary['redis']['cache_hit_rate']:.1f}%")
        
        print("\n🖥️  HEROKU DYNO:")
        print(f"  Memory Usage: {summary['heroku']['memory_usage_percent']:.1f}%")
        print(f"  CPU Usage: {summary['heroku']['cpu_percent']:.1f}%")
        print(f"  Network Sent: {summary['heroku']['network_mb_sent']:.2f} MB")
        print(f"  Network Received: {summary['heroku']['network_mb_recv']:.2f} MB")
        
        print("\n🌐 TOP API ENDPOINTS BY DATA TRANSFER:")
        for i, endpoint in enumerate(summary['top_endpoints'][:5], 1):
            print(f"  {i}. {endpoint['endpoint']}")
            print(f"     Calls: {endpoint['count']} | Total: {endpoint['total_mb']:.2f} MB | Avg: {endpoint['avg_response_kb']:.2f} KB")
        
        print("="*60)


# Global monitor instance
monitor = EgressMonitor()


# Decorators for automatic monitoring
def monitor_api_endpoint(endpoint=None):
    """Decorator to monitor API endpoint calls"""
    if callable(endpoint):
        # Called without parentheses: @monitor_api_endpoint
        func = endpoint
        endpoint = None
        return monitor_api_endpoint(endpoint)(func)
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            
            # Get request size
            request_size = len(request.body) if hasattr(request, 'body') else 0
            
            # Call the actual function
            response = func(request, *args, **kwargs)
            
            # Get response size
            response_size = len(response.content) if hasattr(response, 'content') else 0
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # ms
            
            # Log the API call
            endpoint_name = endpoint or request.path
            monitor.log_api_call(
                endpoint_name,
                method=request.method,
                request_size=request_size,
                response_size=response_size,
                duration=duration
            )
            
            return response
        return wrapper
    return decorator


def monitor_database_query(func):
    """Decorator to monitor database queries"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Get the SQL query if available
        query = str(args[0]) if args else "Unknown query"
        
        # Execute query
        result = func(*args, **kwargs)
        
        # Estimate response size
        response_size = 0
        if hasattr(result, '__len__'):
            # Rough estimate: 100 bytes per row
            response_size = len(result) * 100
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000  # ms
        
        # Log the query
        monitor.log_supabase_query(
            query=query,
            response_size=response_size,
            duration=duration
        )
        
        return result
    return wrapper


def monitor_redis_command(func):
    """Decorator to monitor Redis commands"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        command = func.__name__.upper()
        
        # Execute command
        result = func(self, *args, **kwargs)
        
        # Estimate response size
        response_size = len(str(result)) if result else 0
        
        # Log the command
        monitor.log_redis_command(
            command=command,
            args=args,
            response_size=response_size
        )
        
        return result
    return wrapper


# Background monitoring task
def start_monitoring_daemon():
    """Start background monitoring daemon"""
    import threading
    
    def monitor_loop():
        while True:
            try:
                # Update system metrics every 30 seconds
                monitor.update_system_metrics()
                
                # Save snapshot to cache
                cache.set('egress_monitor:latest_summary', monitor.get_summary(), timeout=300)
                
                # Log summary every 5 minutes
                if int(time.time()) % 300 == 0:
                    logger.info("Periodic summary:")
                    monitor.print_summary()
                
                time.sleep(30)
            except Exception as e:
                logger.error(f"Monitor daemon error: {e}")
                time.sleep(60)
    
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    logger.info("Monitoring daemon started")