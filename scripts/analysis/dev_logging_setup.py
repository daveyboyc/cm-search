#!/usr/bin/env python3
"""
Test logging configuration for egress optimization monitoring
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def test_logging_configuration():
    """Test that logging is properly configured for optimization monitoring"""
    print("🔧 TESTING LOGGING CONFIGURATION")
    print("=" * 50)
    
    try:
        # Test Django settings
        from django.conf import settings
        print(f"✅ Django configured successfully")
        print(f"   DEBUG = {settings.DEBUG}")
        
        # Check logging configuration
        if hasattr(settings, 'LOGGING'):
            logging_config = settings.LOGGING
            print(f"✅ LOGGING configuration found")
            
            # Check if our optimized view loggers are configured
            loggers = logging_config.get('loggers', {})
            
            optimization_loggers = [
                'checker.views_company_optimized',
                'checker.views_technology_optimized', 
                'checker.views_search_map_simple'
            ]
            
            for logger_name in optimization_loggers:
                if logger_name in loggers:
                    print(f"✅ {logger_name} logger configured")
                else:
                    print(f"⚠️  {logger_name} logger not found (will use parent)")
        else:
            print("❌ No LOGGING configuration found in settings")
            
    except Exception as e:
        print(f"❌ Django configuration error: {e}")
        return False
        
    print()
    
    # Test importing the optimized views and their loggers
    print("📋 TESTING OPTIMIZED VIEW IMPORTS")
    print("-" * 30)
    
    views_to_test = [
        ('checker.views_company_optimized', 'company_detail_optimized'),
        ('checker.views_technology_optimized', 'technology_detail_map'),
        ('checker.views_search_map_simple', 'search_map_view_simple')
    ]
    
    for module_name, view_name in views_to_test:
        try:
            module = __import__(module_name, fromlist=[view_name])
            view_func = getattr(module, view_name)
            logger = getattr(module, 'logger', None)
            
            print(f"✅ {module_name}")
            print(f"   View: {view_name} ✓")
            print(f"   Logger: {'✓' if logger else '❌'}")
            
            # Test logger functionality
            if logger:
                logger.info(f"🧪 TEST LOG: {view_name} logger working!")
                
        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")
        except AttributeError as e:
            print(f"❌ {module_name}: Missing attribute - {e}")
        except Exception as e:
            print(f"❌ {module_name}: Unexpected error - {e}")
    
    print()
    print("🔍 TESTING LOG OUTPUT")
    print("-" * 20)
    
    # Test logging directly
    import logging
    
    # Test each logger
    for logger_name in ['checker.views_company_optimized', 'checker.views_technology_optimized', 'checker.views_search_map_simple']:
        try:
            logger = logging.getLogger(logger_name)
            logger.info(f"🧪 TEST: {logger_name} optimization logging working!")
        except Exception as e:
            print(f"❌ Logger {logger_name} failed: {e}")
    
    print()
    print("✅ LOGGING TEST COMPLETE!")
    print("Look above for test log messages starting with '🧪 TEST'")
    print()
    
    return True

def show_what_to_expect():
    """Show what optimization logs should look like"""
    print("📊 EXPECTED OPTIMIZATION LOG FORMAT")
    print("=" * 50)
    print()
    print("When you make requests to optimized views, you should see logs like:")
    print()
    print("🚀 EGRESS-OPTIMIZED company view for 'GRIDBEYOND LIMITED':")
    print("   📊 Total locations: 323")
    print("   📋 Displayed: 50 items (page 1)")
    print("   🔍 Metadata sample: 100 locations")
    print("   💾 Database queries: 4")
    print("   📦 Rows fetched: 150")
    print("   📊 Estimated data: 45,000 bytes (43.9 KB)")
    print("   ⏱️  Load time: 0.087s")
    print("   🔧 Filters: status=all, auction=all")
    print("   💡 Estimated egress reduction: 88.4% (387,600 → 45,000 bytes)")
    print()
    print("🗺️  EGRESS-OPTIMIZED technology map for 'DSR':")
    print("   📊 Total locations: 1,247")
    print("   📋 Displayed: 25 items (page 1)")
    print("   🔍 Metadata sample: 100 locations")
    print("   💾 Database queries: 5")
    print("   📦 Rows fetched: 125")
    print("   📊 Estimated data: 62,500 bytes (61.0 KB)")
    print("   ⏱️  Load time: 0.134s")
    print("   💡 Estimated egress reduction: 95.7% (1,496,400 → 62,500 bytes)")
    print()
    print("🔍 KEY METRICS TO WATCH:")
    print("   ✅ Database queries: Should be 3-6 (not 10-100+)")
    print("   ✅ Rows fetched: Should be <200 (not 1000+)")
    print("   ✅ Load time: Should be <0.5s (not 2-5s)")
    print("   ✅ Egress reduction: Should be 90%+ (huge savings)")
    print()
    print("❌ WARNING SIGNS:")
    print("   - No 'EGRESS-OPTIMIZED' messages")
    print("   - Database queries > 10")
    print("   - Load times > 1 second")
    print("   - Low egress reduction (<80%)")

def show_testing_commands():
    """Show commands to test the optimizations"""
    print("🧪 TESTING COMMANDS")
    print("=" * 30)
    print()
    print("1. Start Django server:")
    print("   python manage.py runserver")
    print()
    print("2. Test optimized endpoints (in another terminal):")
    print()
    print("   # Company views")
    print("   curl http://localhost:8000/company-optimized/gridbeyondlimited/")
    print("   curl http://localhost:8000/company-map/ENEL%20X%20UK%20LIMITED/")
    print()
    print("   # Technology views")
    print("   curl http://localhost:8000/technology-map/DSR/")
    print("   curl http://localhost:8000/technology-optimized/Battery/")
    print()
    print("   # Search views")
    print("   curl http://localhost:8000/map/?query=london")
    print("   curl http://localhost:8000/map/?query=battery&status=active")
    print()
    print("3. Watch the Django server console for optimization logs!")

if __name__ == "__main__":
    print("🚀 EGRESS OPTIMIZATION LOGGING TEST")
    print("=" * 60)
    
    success = test_logging_configuration()
    
    if success:
        print()
        show_what_to_expect()
        print()
        show_testing_commands()
        print()
        print("✅ SETUP COMPLETE!")
        print("Start the Django server and make test requests to see optimization logs! 🎉")
    else:
        print("❌ Setup issues detected. Check errors above.")