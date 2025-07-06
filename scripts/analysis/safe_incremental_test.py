#!/usr/bin/env python3
"""
Safe incremental testing script for database updates
"""
import os
import django
import subprocess
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from test_redis_monitoring import get_redis_stats, check_database_counts

def run_command_with_monitoring(command, operation_name):
    """Run a command while monitoring Redis"""
    print(f"\n{'='*60}")
    print(f"TESTING: {operation_name}")
    print(f"COMMAND: {command}")
    print(f"{'='*60}")
    
    # Before stats
    before_stats = get_redis_stats()
    before_components, before_cmus = check_database_counts()
    
    print(f"BEFORE:")
    print(f"  📊 Redis: {before_stats['used_memory_mb']:.1f}MB ({before_stats['usage_percent']:.1f}%)")
    print(f"  📦 Components: {before_components:,}")
    print(f"  🏢 CMUs: {before_cmus:,}")
    
    # Safety check
    if before_stats['usage_percent'] > 75:
        print(f"🚨 ABORTING: Redis usage too high ({before_stats['usage_percent']:.1f}%)")
        return False
    
    print(f"\n⏳ Running: {operation_name}...")
    start_time = time.time()
    
    try:
        # Run the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=600)
        elapsed = time.time() - start_time
        
        print(f"✅ Completed in {elapsed:.1f} seconds")
        
        # After stats
        after_stats = get_redis_stats()
        after_components, after_cmus = check_database_counts()
        
        print(f"\nAFTER:")
        print(f"  📊 Redis: {after_stats['used_memory_mb']:.1f}MB ({after_stats['usage_percent']:.1f}%)")
        print(f"  📦 Components: {after_components:,} (+{after_components - before_components:,})")
        print(f"  🏢 CMUs: {after_cmus:,} (+{after_cmus - before_cmus:,})")
        
        # Calculate impact
        redis_increase = after_stats['used_memory_mb'] - before_stats['used_memory_mb']
        print(f"\n📈 IMPACT:")
        print(f"  Redis memory: +{redis_increase:.2f}MB")
        print(f"  New components: {after_components - before_components:,}")
        print(f"  New CMUs: {after_cmus - before_cmus:,}")
        
        # Safety assessment
        if after_stats['usage_percent'] > 80:
            print(f"🚨 CRITICAL: Redis usage now > 80%!")
        elif after_stats['usage_percent'] > 70:
            print(f"⚠️  WARNING: Redis usage now > 70%")
        else:
            print(f"✅ SAFE: Redis usage still manageable")
            
        # Show command output if there were errors
        if result.returncode != 0:
            print(f"\n❌ Command failed with return code {result.returncode}")
            print("STDERR:", result.stderr[-500:])  # Last 500 chars
            
        return True
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def test_incremental_crawl():
    """Test incremental crawling with monitoring"""
    
    print(f"🧪 INCREMENTAL CRAWL TEST")
    print(f"{'='*60}")
    
    # Step 1: Test tiny crawl (5 CMUs)
    print("\n🔬 STEP 1: Micro test (5 CMUs)")
    success = run_command_with_monitoring(
        "source venv/bin/activate && python manage.py crawl_to_database --limit 5 --sleep 2.0",
        "Crawl 5 CMUs"
    )
    
    if not success:
        print("❌ Micro test failed, aborting")
        return False
        
    # Check if we should continue
    stats = get_redis_stats()
    if stats['usage_percent'] > 70:
        print(f"⚠️  Redis usage high ({stats['usage_percent']:.1f}%), stopping here")
        return False
        
    # Step 2: Small crawl (50 CMUs)
    print("\n🔬 STEP 2: Small test (50 CMUs)")
    input("\nPress Enter to continue with 50 CMUs, or Ctrl+C to stop...")
    
    success = run_command_with_monitoring(
        "source venv/bin/activate && python manage.py crawl_to_database --limit 50 --sleep 1.5",
        "Crawl 50 CMUs"
    )
    
    if not success:
        print("❌ Small test failed")
        return False
        
    # Step 3: Test cache building
    stats = get_redis_stats()
    if stats['usage_percent'] < 60:
        print("\n🔬 STEP 3: Test cache building")
        input("\nPress Enter to test cache building, or Ctrl+C to stop...")
        
        # Test location mapping (most memory intensive)
        success = run_command_with_monitoring(
            "source venv/bin/activate && python manage.py build_location_mapping --force",
            "Build location mapping"
        )
        
        if success:
            stats = get_redis_stats()
            print(f"\n📊 After cache build: {stats['used_memory_mb']:.1f}MB ({stats['usage_percent']:.1f}%)")
            
            if stats['usage_percent'] < 70:
                print("✅ Cache building looks safe for larger operations")
            else:
                print("⚠️  Cache building uses significant memory - proceed carefully")
    
    return True

if __name__ == "__main__":
    print("🚀 Starting safe incremental test...")
    test_incremental_crawl()