#!/usr/bin/env python3
"""
Test cache rebuilding impact on Redis memory
"""
import os
import django
import subprocess
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from test_redis_monitoring import get_redis_stats

def test_cache_command(command, description):
    """Test a single cache command with before/after monitoring"""
    print(f"\n{'='*60}")
    print(f"TESTING: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*60}")
    
    # Before stats
    before_stats = get_redis_stats()
    
    print(f"BEFORE:")
    print(f"  📊 Redis: {before_stats['used_memory_mb']:.1f}MB ({before_stats['usage_percent']:.1f}%)")
    print(f"  🔑 Keys: {before_stats['total_keys']:,}")
    print(f"  🎯 Status: {before_stats['status']}")
    
    # Safety check
    if before_stats['usage_percent'] > 75:
        print(f"🚨 ABORTING: Redis usage too high ({before_stats['usage_percent']:.1f}%)")
        return False
    
    print(f"\n⏳ Running: {description}...")
    start_time = time.time()
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=600)
        elapsed = time.time() - start_time
        
        print(f"✅ Completed in {elapsed:.1f} seconds")
        
        # After stats
        after_stats = get_redis_stats()
        
        print(f"\nAFTER:")
        print(f"  📊 Redis: {after_stats['used_memory_mb']:.1f}MB ({after_stats['usage_percent']:.1f}%)")
        print(f"  🔑 Keys: {after_stats['total_keys']:,} (+{after_stats['total_keys'] - before_stats['total_keys']:,})")
        print(f"  🎯 Status: {after_stats['status']}")
        
        # Calculate impact
        memory_increase = after_stats['used_memory_mb'] - before_stats['used_memory_mb']
        key_increase = after_stats['total_keys'] - before_stats['total_keys']
        
        print(f"\n📈 IMPACT:")
        print(f"  Memory: +{memory_increase:.2f}MB")
        print(f"  Keys: +{key_increase:,}")
        
        if memory_increase > 0:
            print(f"  Avg per key: {memory_increase / max(key_increase, 1):.3f}MB")
        
        # Safety assessment
        if after_stats['usage_percent'] > 80:
            print(f"🚨 CRITICAL: Redis usage now > 80%!")
            print(f"   🛑 STOP operations and run cleanup")
            return False
        elif after_stats['usage_percent'] > 70:
            print(f"⚠️  WARNING: Redis usage now > 70%")
            print(f"   📊 Monitor closely")
        elif memory_increase > 50:
            print(f"⚠️  WARNING: Large memory increase (+{memory_increase:.1f}MB)")
        else:
            print(f"✅ SAFE: Memory impact manageable")
            
        # Show some output if command failed
        if result.returncode != 0:
            print(f"\n❌ Command failed (exit code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr[-200:]}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cache_rebuilding():
    """Test incremental cache rebuilding"""
    print(f"🧪 REDIS CACHE IMPACT TESTING")
    print(f"Testing cache commands to see Redis memory impact")
    
    # Test 1: Location mapping (usually the biggest)
    success = test_cache_command(
        "source venv/bin/activate && python manage.py build_location_mapping --force",
        "Location mapping cache"
    )
    
    if not success:
        print("❌ Location mapping failed, stopping tests")
        return
    
    # Check if we should continue
    stats = get_redis_stats()
    if stats['usage_percent'] > 70:
        print(f"\n⚠️  Redis usage high ({stats['usage_percent']:.1f}%), stopping here")
        return
    
    # Test 2: Company index
    success = test_cache_command(
        "source venv/bin/activate && python manage.py build_company_index --force",
        "Company index cache"
    )
    
    if not success:
        return
        
    # Check Redis state
    stats = get_redis_stats()
    if stats['usage_percent'] > 70:
        print(f"\n⚠️  Redis usage high ({stats['usage_percent']:.1f}%), skipping map cache")
        return
    
    # Test 3: Small map cache (just one technology)
    print(f"\n🤔 Redis still has room. Test small map cache?")
    choice = input("Test Gas technology map cache? (y/N): ").lower().strip()
    
    if choice == 'y':
        success = test_cache_command(
            "source venv/bin/activate && python manage.py build_map_cache --technology Gas",
            "Gas technology map cache"
        )
    
    # Final summary
    final_stats = get_redis_stats()
    print(f"\n{'='*60}")
    print(f"FINAL REDIS STATE")
    print(f"{'='*60}")
    print(f"  📊 Memory: {final_stats['used_memory_mb']:.1f}MB ({final_stats['usage_percent']:.1f}%)")
    print(f"  🔑 Keys: {final_stats['total_keys']:,}")
    print(f"  🎯 Status: {final_stats['status']}")
    
    if final_stats['usage_percent'] < 60:
        print(f"\n✅ CONCLUSION: Redis can handle more cache operations")
        print(f"   Safe to proceed with larger database update")
    elif final_stats['usage_percent'] < 75:
        print(f"\n🟡 CONCLUSION: Redis usage moderate")
        print(f"   Proceed carefully with monitoring")
    else:
        print(f"\n🚨 CONCLUSION: Redis usage high")
        print(f"   Cleanup needed before major operations")

if __name__ == "__main__":
    test_cache_rebuilding()