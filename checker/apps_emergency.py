from django.apps import AppConfig
import logging
import os


class CheckerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "checker"
    
    def ready(self):
        """
        Emergency startup - minimal Redis usage
        """
        # Skip checks for migration commands
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return

        logger = logging.getLogger(__name__)
        
        # EMERGENCY MODE
        emergency_mode = os.environ.get('REDIS_EMERGENCY_MODE', 'true').lower() == 'true'
        
        if emergency_mode:
            logger.warning("🚨 REDIS EMERGENCY MODE ACTIVE - Minimal Redis usage")
            logger.warning("Map caching: DISABLED")
            logger.warning("Search caching: DISABLED") 
            logger.warning("Using in-memory caching where possible")
            
            # Set emergency flags
            os.environ['DISABLE_MAP_CACHE'] = 'true'
            os.environ['DISABLE_SEARCH_CACHE'] = 'true'
            os.environ['USE_MINIMAL_CACHE'] = 'true'
        else:
            # Normal startup checks
            logger.info("Starting normal cache validation...")
            
            # Only load absolutely essential data
            try:
                from .services.data_access import validate_essential_cache
                validate_essential_cache()
            except Exception as e:
                logger.error(f"Cache validation error: {e}")
                # Don't crash - continue with degraded performance