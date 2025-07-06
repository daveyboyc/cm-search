"""
Simple monitoring decorators
"""
import time
import functools
import os
from .simple_monitor import log_api_call

# Try to import psutil for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[MONITOR] psutil not available, memory monitoring disabled")

def monitor_api(func):
    """Enhanced decorator to monitor API calls with memory tracking"""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        
        # Get initial memory usage (if psutil available)
        memory_before = None
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                memory_before = process.memory_info()
                print(f"[MEMORY] Before: RSS={memory_before.rss/1024/1024:.1f}MB, VMS={memory_before.vms/1024/1024:.1f}MB")
            except Exception as e:
                print(f"[MEMORY] Error getting initial memory: {e}")
        
        # Debug logging
        print(f"[MONITOR] API Call Started: {request.method} {request.path}")
        
        # Execute the function
        response = func(request, *args, **kwargs)
        
        # Get final memory usage (if psutil available)
        memory_delta_mb = 0
        memory_rss_mb = 0
        if PSUTIL_AVAILABLE and memory_before:
            try:
                memory_after = process.memory_info()
                memory_delta_mb = (memory_after.rss - memory_before.rss) / 1024 / 1024
                memory_rss_mb = memory_after.rss / 1024 / 1024
                print(f"[MEMORY] After: RSS={memory_rss_mb:.1f}MB, Delta: {memory_delta_mb:+.1f}MB")
            except Exception as e:
                print(f"[MEMORY] Error getting final memory: {e}")
        
        # Calculate metrics
        duration = (time.time() - start_time) * 1000
        response_size = 0
        
        if hasattr(response, 'content'):
            response_size = len(response.content)
        
        # Enhanced logging with memory info
        print(f"[MONITOR] API Call Completed: {request.path}")
        print(f"[EGRESS] Response Size: {response_size:,} bytes ({response_size/1024/1024:.2f}MB)")
        print(f"[PERFORMANCE] Duration: {duration:.2f}ms")
        
        # Alert on large responses or memory spikes
        if response_size > 10 * 1024 * 1024:  # 10MB
            print(f"🚨 [EGRESS ALERT] Large response: {response_size/1024/1024:.2f}MB from {request.path}")
        
        if memory_delta_mb > 100:  # 100MB memory increase
            print(f"🚨 [MEMORY ALERT] Memory spike: +{memory_delta_mb:.1f}MB during {request.path}")
        
        if duration > 5000:  # 5 seconds
            print(f"🚨 [PERFORMANCE ALERT] Slow response: {duration:.0f}ms for {request.path}")
        
        # Log the call with enhanced metrics
        log_api_call(
            endpoint=request.path,
            method=request.method,
            response_size=response_size,
            duration=duration,
            memory_delta_mb=memory_delta_mb,
            memory_rss_mb=memory_rss_mb
        )
        
        return response
    return wrapper