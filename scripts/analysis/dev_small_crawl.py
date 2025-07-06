#!/usr/bin/env python3
"""
Test a small crawl with new CMUs and monitor Redis impact
"""
import os
import django
import subprocess
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from test_redis_monitoring import get_redis_stats

def test_small_crawl():
    """Test crawling 5 new CMUs with monitoring"""
    print("🧪 TESTING: Small crawl with Redis monitoring")
    print("=" * 60)
    
    # Before stats
    before_stats = get_redis_stats()
    before_components = Component.objects.count()
    before_cmus = Component.objects.values('cmu_id').distinct().count()
    
    print(f"BEFORE CRAWL:")
    print(f"  📊 Redis: {before_stats['used_memory_mb']:.1f}MB ({before_stats['usage_percent']:.1f}%)")
    print(f"  📦 Components: {before_components:,}")
    print(f"  🏢 CMUs: {before_cmus:,}")
    
    if before_stats['usage_percent'] > 70:
        print(f"🚨 Redis usage too high, aborting")
        return
    
    print(f"\n⏳ Crawling 5 new CMUs starting from offset 10542...")
    start_time = time.time()
    
    # Run crawl command
    cmd = "source venv/bin/activate && python manage.py crawl_to_database --limit 5 --offset 10542 --sleep 1.0"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        elapsed = time.time() - start_time
        
        print(f"✅ Command completed in {elapsed:.1f} seconds")
        print(f"Return code: {result.returncode}")
        
        # Show last few lines of output
        if result.stdout:
            print("Last few lines of output:")
            lines = result.stdout.strip().split('\n')[-10:]
            for line in lines:
                if line.strip():
                    print(f"  {line}")
        
        if result.stderr and result.returncode != 0:
            print("Errors:")
            print(f"  {result.stderr[-200:]}")
        
        # After stats  
        after_stats = get_redis_stats()
        after_components = Component.objects.count()
        after_cmus = Component.objects.values('cmu_id').distinct().count()
        
        print(f"\nAFTER CRAWL:")
        print(f"  📊 Redis: {after_stats['used_memory_mb']:.1f}MB ({after_stats['usage_percent']:.1f}%)")
        print(f"  📦 Components: {after_components:,} (+{after_components - before_components:,})")
        print(f"  🏢 CMUs: {after_cmus:,} (+{after_cmus - before_cmus:,})")
        
        # Calculate impacts
        redis_increase = after_stats['used_memory_mb'] - before_stats['used_memory_mb']
        
        print(f"\n📈 IMPACT ANALYSIS:")
        print(f"  Redis memory: +{redis_increase:.2f}MB")
        print(f"  New components: {after_components - before_components:,}")
        print(f"  New CMUs: {after_cmus - before_cmus:,}")
        
        if after_components > before_components:
            components_per_mb = (after_components - before_components) / max(redis_increase, 0.01)
            print(f"  Redis efficiency: ~{components_per_mb:.0f} components per MB")
        
        # Safety assessment
        if after_stats['usage_percent'] > 80:
            print(f"🚨 CRITICAL: Redis usage now > 80%!")
            print(f"   STOP all operations and run cleanup")
        elif after_stats['usage_percent'] > 70:
            print(f"⚠️  WARNING: Redis usage now > 70%")
            print(f"   Monitor closely, consider smaller batches")
        elif redis_increase > 1.0:
            print(f"⚠️  WARNING: High Redis memory increase (+{redis_increase:.1f}MB)")
            print(f"   Monitor for memory leaks")
        else:
            print(f"✅ SAFE: Low impact on Redis")
            
        # Recommendations
        if after_components > before_components and redis_increase < 0.5:
            print(f"\n🎯 RECOMMENDATION:")
            print(f"   Safe to proceed with larger batches (50-100 CMUs)")
            print(f"   Estimated Redis impact for 1526 CMUs: ~{redis_increase * 1526 / 5:.1f}MB")
        elif redis_increase > 2.0:
            print(f"\n🎯 RECOMMENDATION:")
            print(f"   High Redis usage - use smaller batches or cleanup between operations")
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_small_crawl()