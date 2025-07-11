import os
import json
import re
import redis
import logging
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


def normalize(text):
    """Lowercase and remove all whitespace."""
    if not isinstance(text, str):
        return ""
    return "".join(text.lower().split())


def slugify(text):
    """
    Convert text to SEO-friendly slug
    Example: 'OCTOPUS ENERGY LIMITED' -> 'octopus-energy-limited'
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars except spaces and hyphens
    text = re.sub(r'[-\s]+', '-', text)   # Replace spaces and multiple hyphens with single hyphen
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


def deslugify(slug):
    """
    Convert slug back to display format
    Example: 'octopus-energy-limited' -> 'OCTOPUS ENERGY LIMITED'
    """
    if not isinstance(slug, str):
        return ""
    
    # Replace hyphens with spaces and convert to uppercase
    return slug.replace('-', ' ').upper()


def get_cache_key(prefix, identifier):
    """
    Generate consistent and safe cache keys with standard format.
    Ensures keys are safe for all cache backends including memcached.
    """
    if not isinstance(identifier, str):
        identifier = str(identifier)
    
    # For spaces or special chars, use a hash to ensure valid cache keys
    if ' ' in identifier or not identifier.isalnum():
        # Create a hash of the identifier
        identifier_hash = hashlib.md5(identifier.encode('utf-8')).hexdigest()
        safe_identifier = identifier_hash
    else:
        # For simple identifiers, just use the lowercase version
        safe_identifier = identifier.lower()
        
    return f"{prefix}_{safe_identifier}"


def get_json_path(cmu_id):
    """Get the path to the JSON file for a given CMU ID."""
    if not cmu_id:
        return None

    # Get first character of CMU ID as prefix
    prefix = cmu_id[0].upper() if cmu_id else "0"

    # Path for the file that would contain this CMU ID
    json_dir = os.path.join(settings.BASE_DIR, 'json_data')
    json_path = os.path.join(json_dir, f'components_{prefix}.json')

    return json_path


def ensure_directory_exists(directory_path):
    """Ensure that a directory exists, creating it if necessary."""
    os.makedirs(directory_path, exist_ok=True)


def matched_component(component1, component2):
    """Helper function to determine if two components match"""
    # Define key fields to compare
    key_fields = ["CMU ID", "Location and Post Code", "Description of CMU Components"]

    # Check if all key fields match
    for field in key_fields:
        if component1.get(field) != component2.get(field):
            return False

    return True


def format_location_list(locations, components):
    """
    Format a list of locations with their components.
    Returns HTML string.
    """
    html = "<ul class='list-unstyled'>"

    for location in sorted(locations):
        # Add components at this location
        location_components = [c for c in components if c.get("Location and Post Code", "") == location]

        # Add debug info
        component_count = len(location_components)

        # Create component ID for first component (for linking)
        component_id = ""
        if location_components and "CMU ID" in location_components[0]:
            cmu_id = location_components[0].get("CMU ID", "")
            if cmu_id:
                loc_normalized = normalize(location).replace("/", "_")
                component_id = f"{cmu_id}_{loc_normalized}"

        # Format location as a blue link if we have a component ID
        location_html = location
        if component_id:
            location_html = f'<a href="/component/{component_id}/" style="color: blue; text-decoration: underline;">{location}</a>'

        html += f"""
            <li class="mb-2">
                <strong>{location_html}</strong> <span class="text-muted">({component_count} components)</span>
                <ul class="ms-3">
        """

        # Add debug
        if not location_components:
            html += f"""
                <li><i>No components found for this location</i></li>
            """
            continue

        for component in location_components:
            desc = component.get("Description of CMU Components", "N/A")
            tech = component.get("Generating Technology Class", "")
            auction = component.get("Auction Name", "")
            delivery_year = component.get("Delivery Year", "")
            
            # Get both types of IDs
            system_id = component.get("_id", "")[:8] if component.get("_id") else ""
            component_id_value = component.get("Component ID", "") if component.get("Component ID") else ""

            # Extract auction year and type
            auction_year = ""
            auction_type = ""
            if auction:
                # Parse auction info - example format: "T-4 2024/25"
                parts = auction.split()
                if len(parts) >= 1:
                    auction_type = parts[0]  # T-1, T-4, etc.
                if len(parts) >= 2:
                    auction_year = parts[1]  # 2024/25, etc.

            # Create badges
            auction_badge = ""
            if auction_type:
                badge_color = "info" if auction_type == "T-4" else "warning" if auction_type == "T-1" else "secondary"
                auction_badge = f'<span class="badge bg-{badge_color} ms-1">{auction_type}</span>'

            year_info = f'<span class="text-muted ms-1">(Auction: {auction_year}, Delivery: {delivery_year})</span>' if auction_year else ""

            # Add both IDs if available
            id_info = ""
            if system_id:
                id_info += f' <small class="text-muted">[ID: {system_id}]</small>'
            if component_id_value:
                id_info += f' <small class="text-muted ms-1">[Component ID: {component_id_value}]</small>'

            # Now add the IDs to the component line - this was missing!
            html += f"""
                <li><i>{desc}</i>{f" - {tech}" if tech else ""} {auction_badge} {year_info} {id_info}</li>
            """

        html += """
                </ul>
            </li>
        """

    html += "</ul>"
    return html


def safe_url_param(value):
    """Convert spaces to underscores for URL parameters"""
    return str(value).replace(' ', '_')


def from_url_param(value):
    """Convert underscores back to spaces"""
    return str(value).replace('_', ' ')


# Smart Cache Management for Redis Memory Optimization
class SmartCacheManager:
    """Manages Redis cache with memory monitoring"""
    
    def __init__(self):
        self.redis_url = settings.CACHES['default']['LOCATION']
        self.threshold = 0.7  # Clear cache at 70% memory usage
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(self.redis_url)
            logger.info("Smart cache manager initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
    
    def check_memory_usage(self):
        """Check Redis memory usage percentage"""
        if not self.redis_client:
            return 0.0
        
        try:
            info = self.redis_client.info('memory')
            used_memory = info.get('used_memory', 0)
            
            # Heroku Redis free tier is 30MB
            max_memory = 30 * 1024 * 1024  # 30MB in bytes
            
            usage_percentage = used_memory / max_memory
            logger.debug(f"Redis memory usage: {usage_percentage:.1%} ({used_memory / 1024 / 1024:.1f}MB / 30MB)")
            return usage_percentage
        except Exception as e:
            logger.error(f"Error checking Redis memory: {e}")
            return 0.0
    
    def clear_cache_if_needed(self):
        """Clear cache if memory usage exceeds threshold"""
        usage = self.check_memory_usage()
        
        if usage >= self.threshold:
            logger.warning(f"Redis memory usage at {usage:.1%}, clearing cache...")
            try:
                cache.clear()
                logger.info("Cache cleared successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
        return False


# Global instance
smart_cache_manager = SmartCacheManager()


def smart_cache(timeout):
    """
    Smart cache decorator that monitors memory usage
    and clears cache when approaching limits
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check and clear cache if needed before caching
            smart_cache_manager.clear_cache_if_needed()
            
            # Apply standard cache_page decorator
            cached_view = cache_page(timeout)(view_func)
            return cached_view(request, *args, **kwargs)
        return wrapper
    return decorator


# Convenience decorators with appropriate timeouts
# Reduced timeouts to save Redis memory
short_cache = smart_cache(60)  # 1 minute (was 2)
medium_cache = smart_cache(120)  # 2 minutes (was 5)
long_cache = smart_cache(300)  # 5 minutes (was 10)