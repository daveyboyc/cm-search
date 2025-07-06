from django.apps import AppConfig
from django.conf import settings
import redis
import logging
import time
import threading


class CheckerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "checker"
    
    def ready(self):
        """
        Startup checks for required cache data
        """
        # Skip checks for migration commands
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        
        # EMERGENCY: Skip ALL startup checks in emergency mode
        import os
        if os.environ.get('REDIS_EMERGENCY_MODE', 'false').lower() == 'true':
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("🚨 EMERGENCY MODE: Skipping all startup cache validation to reduce Redis traffic")
            return

        try:
            # Use a separate thread for these checks to not block app startup
            def perform_startup_checks():
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Performing startup cache validation...")
                
                # Check Redis connectivity
                try:
                    redis_client = redis.from_url(settings.CACHES['default']['LOCATION'])
                    redis_client.ping()
                    logger.info("✅ Redis connection successful")
                except Exception as e:
                    logger.error(f"❌ Redis connection failed: {str(e)}")
                
                # Check location mapping (try fast version first)
                try:
                    try:
                        from .services.postcode_helpers_fast import startup_check_redis_mapping
                        logger.info("Using FAST postcode helpers")
                    except ImportError:
                        from .services.postcode_helpers import startup_check_redis_mapping
                        logger.info("Using standard postcode helpers")
                    mapping_status = startup_check_redis_mapping()
                    if mapping_status:
                        logger.info(f"✅ REDIS LOCATION MAPPING LOADED: Found pre-built mapping")
                        logger.info(f"✅ Location lookups will use Redis cache and NOT timeout or rebuild each time")
                    else:
                        logger.warning(f"❓ Location mapping not found in Redis - will be built on first request")
                except Exception as e:
                    logger.error(f"❌ Error checking location mapping: {str(e)}")
                
                # Check CMU dataframe in Redis
                try:
                    from .services.data_access import get_cmu_dataframe
                    df, load_time = get_cmu_dataframe()
                    if df is not None:
                        row_count = len(df)
                        logger.info(f"✅ CMU DATAFRAME LOADED: Found cached dataframe with {row_count} records")
                        logger.info(f"✅ CMU searches will use Redis cache and be much faster (saving ~1.4s per search)")
                    else:
                        logger.warning(f"❓ CMU dataframe not found in Redis - will be loaded from CSV on first request")
                except Exception as e:
                    logger.error(f"❌ Error checking CMU dataframe: {str(e)}")
                
                # Check PostgreSQL company data
                try:
                    from .models_company import Company
                    company_count = Company.objects.count()
                    if company_count > 0:
                        logger.info(f"✅ POSTGRESQL COMPANIES LOADED: Found {company_count} companies in database")
                        logger.info(f"✅ Company searches will use PostgreSQL with fast indexed queries")
                    else:
                        logger.warning(f"❓ No companies found in PostgreSQL - run 'python manage.py build_company_postgresql'")
                except Exception as e:
                    logger.error(f"❌ Error checking PostgreSQL companies: {str(e)}")
                
                # Check map cache in Redis
                try:
                    from .services.map_cache import get_cached_map_data
                    # Try to fetch a common view (UK with Wind technology)
                    common_params = {
                        'technology': 'Wind',
                        'north': '58.7',
                        'south': '50.0',
                        'east': '1.8',
                        'west': '-8.2',
                        'detail_level': 'minimal'
                    }
                    cached_map_data = get_cached_map_data(common_params)
                    if cached_map_data:
                        logger.info(f"✅ MAP CACHE LOADED: Found pre-cached map views")
                        logger.info(f"✅ Map requests will use Redis cache and be much faster (saving ~0.7s per view)")
                    else:
                        logger.warning(f"❓ Map cache not found in Redis - run 'python manage.py build_map_cache'")
                except Exception as e:
                    logger.error(f"❌ Error checking map cache: {str(e)}")
            
            # Start the checks in a background thread
            thread = threading.Thread(target=perform_startup_checks)
            thread.daemon = True
            thread.start()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during startup checks: {str(e)}")
