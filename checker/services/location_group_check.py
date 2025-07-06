"""
Check if LocationGroups are built and ready to use.
"""
from django.core.cache import cache
from ..models import LocationGroup, Component
import logging

logger = logging.getLogger(__name__)


def should_use_location_groups():
    """
    Determine if we should use LocationGroups for search.
    Returns True if LocationGroups cover a sufficient percentage of components.
    """
    # Check cache first
    cache_key = 'location_groups_ready'
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Count total valid components (excluding invalid locations)
        total_components = Component.objects.exclude(
            location__isnull=True
        ).exclude(
            location__in=['', 'None', 'N/A', 'NA', 'TBC']
        ).exclude(
            location__icontains='to be confirmed'
        ).count()
        
        # Count LocationGroups
        location_group_count = LocationGroup.objects.count()
        
        # If we have at least 80% coverage, use LocationGroups
        if location_group_count > 0 and total_components > 0:
            # Get total components covered by LocationGroups
            covered_components = LocationGroup.objects.values_list(
                'component_count', flat=True
            )
            total_covered = sum(covered_components)
            
            coverage_percentage = (total_covered / total_components) * 100
            
            logger.info(
                f"LocationGroup coverage: {location_group_count} groups "
                f"covering {total_covered}/{total_components} components "
                f"({coverage_percentage:.1f}%)"
            )
            
            # Use LocationGroups if we have >80% coverage
            result = coverage_percentage > 80
            
            # Cache for 1 hour
            cache.set(cache_key, result, 3600)
            return result
        else:
            logger.info("LocationGroups not ready: insufficient data")
            cache.set(cache_key, False, 300)  # Check again in 5 minutes
            return False
            
    except Exception as e:
        logger.error(f"Error checking LocationGroup readiness: {e}")
        return False


def get_location_groups_stats():
    """Get statistics about LocationGroup coverage."""
    try:
        total_components = Component.objects.exclude(
            location__isnull=True
        ).exclude(
            location__in=['', 'None', 'N/A', 'NA', 'TBC']
        ).count()
        
        location_group_count = LocationGroup.objects.count()
        
        if location_group_count > 0:
            covered_components = LocationGroup.objects.values_list(
                'component_count', flat=True
            )
            total_covered = sum(covered_components)
            coverage_percentage = (total_covered / total_components) * 100
            
            return {
                'location_groups': location_group_count,
                'total_components': total_components,
                'covered_components': total_covered,
                'coverage_percentage': coverage_percentage,
                'is_ready': coverage_percentage > 80
            }
        else:
            return {
                'location_groups': 0,
                'total_components': total_components,
                'covered_components': 0,
                'coverage_percentage': 0,
                'is_ready': False
            }
    except Exception as e:
        logger.error(f"Error getting LocationGroup stats: {e}")
        return None