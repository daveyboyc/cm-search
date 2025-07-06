#!/usr/bin/env python3
"""
Test script to verify the egress optimizations are working
Shows before/after logging comparison
"""
import os
import sys
import django
import requests
import time
from io import StringIO
import logging

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def test_optimization_endpoints():
    """Test the optimized endpoints and capture logging output"""
    
    print("🧪 TESTING EGRESS OPTIMIZATIONS")
    print("=" * 50)
    
    # Test URLs to verify optimizations
    test_urls = [
        {
            'name': 'Company List View (GridBeyond)',
            'url': 'http://localhost:8000/company-optimized/gridbeyondlimited/',
            'expected_reduction': '88%+'
        },
        {
            'name': 'Company Map View (Enel X)',
            'url': 'http://localhost:8000/company-map/ENEL%20X%20UK%20LIMITED/',
            'expected_reduction': '94%+'
        },
        {
            'name': 'Technology Map View (DSR)',
            'url': 'http://localhost:8000/technology-map/DSR/',
            'expected_reduction': '95%+'
        },
        {
            'name': 'Search Map View (London)',
            'url': 'http://localhost:8000/map/?query=london',
            'expected_reduction': '96%+'
        },
        {
            'name': 'Technology List View (Battery)',
            'url': 'http://localhost:8000/technology-optimized/Battery/',
            'expected_reduction': '94%+'
        }
    ]
    
    for test in test_urls:
        print(f"\n🔍 Testing: {test['name']}")
        print(f"📎 URL: {test['url']}")
        print(f"🎯 Expected reduction: {test['expected_reduction']}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            response = requests.get(test['url'], timeout=30)
            load_time = time.time() - start_time
            
            if response.status_code == 200:
                print(f"✅ Status: {response.status_code}")
                print(f"⏱️  Response time: {load_time:.3f}s")
                print(f"📦 Response size: {len(response.content):,} bytes ({len(response.content)/1024:.1f} KB)")
                
                # Check for optimization indicators in response
                content = response.text.lower()
                if 'egress-optimized' in content or 'optimization' in content:
                    print("✅ Optimization detected in response")
                else:
                    print("ℹ️  No optimization indicators found in response")
                    
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"❌ Error: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            
        print()
    
    print("\n📊 WHAT TO LOOK FOR IN LOGS:")
    print("=" * 50)
    print("✅ Look for lines containing:")
    print("   🚀 EGRESS-OPTIMIZED company view")
    print("   🗺️  EGRESS-OPTIMIZED company map") 
    print("   🗺️  EGRESS-OPTIMIZED technology map")
    print("   🗺️  EGRESS-OPTIMIZED search map view")
    print()
    print("📊 Key metrics to verify:")
    print("   📊 Total locations: [large number]")
    print("   📋 Displayed: [small number like 25-50]")
    print("   💾 Database queries: [small number like 3-6]")
    print("   📦 Rows fetched: [small number]")
    print("   💡 Estimated egress reduction: [90%+]")
    print()
    print("❌ Bad signs to watch for:")
    print("   - Load times > 2 seconds")
    print("   - Database queries > 10")
    print("   - Rows fetched > 1000")
    print("   - No egress reduction messages")

def check_log_configuration():
    """Check if logging is properly configured"""
    print("\n🔧 CHECKING LOG CONFIGURATION")
    print("=" * 50)
    
    # Import the optimized views to trigger logger creation
    try:
        from checker.views_company_optimized import logger as company_logger
        from checker.views_technology_optimized import logger as tech_logger
        from checker.views_search_map_simple import logger as search_logger
        
        print("✅ Successfully imported optimized view loggers")
        
        # Test logging
        company_logger.info("🧪 TEST: Company logger working")
        tech_logger.info("🧪 TEST: Technology logger working") 
        search_logger.info("🧪 TEST: Search logger working")
        
        print("✅ Test log messages sent - check console output above")
        
    except ImportError as e:
        print(f"❌ Failed to import loggers: {e}")
    except Exception as e:
        print(f"❌ Logging test failed: {e}")

def show_monitoring_commands():
    """Show commands to monitor the optimizations"""
    print("\n📹 REAL-TIME MONITORING COMMANDS")
    print("=" * 50)
    print("To monitor logs in real-time, run these commands:")
    print()
    print("1. 📊 Start Django development server:")
    print("   python manage.py runserver")
    print()
    print("2. 🔍 In another terminal, monitor logs:")
    print("   tail -f /var/log/django/debug.log  # if using file logging")
    print("   # OR watch console output from runserver")
    print()
    print("3. 🧪 Test endpoints manually:")
    print("   curl http://localhost:8000/company-optimized/gridbeyondlimited/")
    print("   curl http://localhost:8000/technology-map/DSR/")
    print("   curl http://localhost:8000/map/?query=london")
    print()
    print("4. 📈 Look for optimization metrics in logs:")
    print("   grep 'EGRESS-OPTIMIZED' logs.txt")
    print("   grep 'egress reduction' logs.txt")

if __name__ == "__main__":
    print("🚀 EGRESS OPTIMIZATION VERIFICATION TOOL")
    print("=" * 60)
    
    # Check Django is available
    try:
        from django.conf import settings
        print(f"✅ Django configured with DEBUG={settings.DEBUG}")
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        sys.exit(1)
    
    check_log_configuration()
    
    print("\n" + "=" * 60)
    print("📋 INSTRUCTIONS:")
    print("1. Start Django server: python manage.py runserver")
    print("2. Run this test script: python test_optimization_logging.py")
    print("3. Check console output for optimization logs")
    print("=" * 60)
    
    # Ask user if they want to test endpoints
    try:
        test_choice = input("\n🤔 Test optimization endpoints now? (y/n): ").lower().strip()
        if test_choice == 'y':
            test_optimization_endpoints()
        else:
            print("ℹ️  Skipping endpoint tests. Run manually when Django server is running.")
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    
    show_monitoring_commands()
    
    print("\n✅ VERIFICATION COMPLETE!")
    print("Check the console output for egress optimization logs! 🎉")