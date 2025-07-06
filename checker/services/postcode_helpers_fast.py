"""
Fast postcode helpers using static JSON files instead of slow database queries
Reduces location lookup from 5.6s to <10ms
"""
import json
import os
import logging
from functools import lru_cache
from django.conf import settings
import requests
from django.core.cache import cache
import re
import time

logger = logging.getLogger(__name__)

# Base URL for the postcodes.io API
POSTCODES_IO_BASE_URL = "https://api.postcodes.io"

# Cache the static data in memory after first load
_static_cache = {}

@lru_cache(maxsize=1)
def load_static_location_data():
    """Load static location data files into memory (only once)"""
    global _static_cache
    
    if _static_cache:
        return _static_cache
    
    try:
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'cache')
        
        # Load outward code mappings
        with open(os.path.join(static_dir, 'outward_locations.json'), 'r') as f:
            _static_cache['outward_locations'] = json.load(f)
        
        # Load location counts
        with open(os.path.join(static_dir, 'location_counts.json'), 'r') as f:
            _static_cache['location_counts'] = json.load(f)
        
        # Load search index
        with open(os.path.join(static_dir, 'search_index.json'), 'r') as f:
            _static_cache['search_index'] = json.load(f)
        
        # Build reverse mapping (location -> postcodes)
        location_to_postcodes = {}
        for outward, locations in _static_cache['outward_locations'].items():
            for location in locations:
                if location not in location_to_postcodes:
                    location_to_postcodes[location] = []
                location_to_postcodes[location].append(outward)
        
        _static_cache['location_to_postcodes'] = location_to_postcodes
        
        logger.info("✅ Loaded static location data into memory")
        return _static_cache
        
    except Exception as e:
        logger.error(f"Failed to load static data: {e}")
        return {}

def get_location_to_postcodes_mapping(force_rebuild=False):
    """
    FAST VERSION: Returns location to postcodes mapping from static files.
    Replaces the slow database query version that takes 5.6 seconds.
    
    Args:
        force_rebuild (bool): Ignored in fast version
        
    Returns:
        dict: Mapping of location names to lists of postcode outcodes
    """
    start_time = time.time()
    data = load_static_location_data()
    
    if not data:
        logger.error("Failed to load static location data")
        return {}
    
    mapping = data.get('location_to_postcodes', {})
    
    elapsed = time.time() - start_time
    logger.info(f"✅ FAST: Loaded location mapping with {len(mapping)} locations in {elapsed:.3f}s")
    
    return mapping

def startup_check_redis_mapping():
    """
    Check if static location data is available at startup.
    """
    try:
        data = load_static_location_data()
        if data and 'location_to_postcodes' in data:
            location_count = len(data['location_to_postcodes'])
            logger.info(f"✅ STATIC LOCATION MAPPING LOADED: Found pre-built mapping with {location_count} locations")
            logger.info(f"✅ Location lookups will use static files and be INSTANT (<10ms)")
            
            # Output a sample
            if location_count > 0:
                sample_location = list(data['location_to_postcodes'].keys())[0]
                sample_postcodes = data['location_to_postcodes'][sample_location]
                logger.info(f"✅ Sample mapping - Location: '{sample_location}' → Postcodes: {sample_postcodes}")
            
            return True
        else:
            logger.warning("❌ NO STATIC LOCATION MAPPING FOUND")
            return False
    except Exception as e:
        logger.error(f"Error checking static mapping: {e}")
        return False

def get_all_postcodes_for_area(area_name):
    """
    FAST VERSION: Gets postcode prefixes for an area using static files.
    Reduces lookup time from seconds to milliseconds.
    """
    if not area_name or not isinstance(area_name, str):
        return []
    
    start_time = time.time()
    area_name_lower = area_name.lower().strip()
    
    # Load static data
    data = load_static_location_data()
    if not data:
        return []
    
    # Direct location match
    location_to_postcodes = data.get('location_to_postcodes', {})
    if area_name_lower in location_to_postcodes:
        postcodes = location_to_postcodes[area_name_lower]
        elapsed = time.time() - start_time
        logger.info(f"✅ FAST: Found {len(postcodes)} postcodes for '{area_name}' in {elapsed:.3f}s")
        return postcodes
    
    # Check if it's an outward code itself
    outward = area_name.strip().upper()
    if re.match(r'^[A-Z]{1,2}[0-9]{0,2}$', outward):
        logger.debug(f"'{area_name}' appears to be an outcode itself")
        return [outward]
    
    # Search for partial matches
    matching_postcodes = []
    for location, postcodes in location_to_postcodes.items():
        if area_name_lower in location.lower():
            matching_postcodes.extend(postcodes)
    
    if matching_postcodes:
        # Deduplicate
        unique_postcodes = list(set(matching_postcodes))
        elapsed = time.time() - start_time
        logger.info(f"✅ FAST: Found {len(unique_postcodes)} postcodes for partial match '{area_name}' in {elapsed:.3f}s")
        return unique_postcodes[:50]  # Limit results
    
    elapsed = time.time() - start_time
    logger.info(f"No postcodes found for '{area_name}' in {elapsed:.3f}s")
    return []

def get_area_for_any_postcode(postcode):
    """
    FAST VERSION: Determine the area/location for a postcode using static files.
    """
    if not postcode:
        return None
    
    # Extract outward code
    postcode = postcode.strip().upper()
    if " " in postcode:
        outward = postcode.split(" ")[0]
    else:
        # Extract outward code from full postcode
        if len(postcode) >= 5:
            if len(postcode) == 5:
                outward = postcode[:2]
            elif len(postcode) == 6:
                outward = postcode[:3]
            elif len(postcode) == 7:
                outward = postcode[:4] if postcode[3].isdigit() else postcode[:3]
            else:
                outward = postcode[:4] if postcode[3].isdigit() else postcode[:3]
        else:
            outward = postcode
    
    # Load static data
    data = load_static_location_data()
    if not data:
        return None
    
    # Check outward locations mapping
    outward_locations = data.get('outward_locations', {})
    if outward in outward_locations:
        locations = outward_locations[outward]
        if locations:
            return locations[0]  # Return first matching location
    
    return None

# Keep remaining functions that don't need optimization
def validate_postcode(postcode):
    """Validates a postcode using the postcodes.io API."""
    if not postcode or not isinstance(postcode, str):
        return False
    
    postcode_cleaned = postcode.strip().upper().replace(" ", "")
    cache_key = f"postcode_validation_{postcode_cleaned}"
    is_valid = cache.get(cache_key)
    
    if is_valid is None:
        try:
            response = requests.get(f"{POSTCODES_IO_BASE_URL}/postcodes/{postcode_cleaned}/validate")
            response.raise_for_status()
            is_valid = response.json().get("result", False)
            cache.set(cache_key, is_valid, timeout=3600 * 24)  # Cache for 24 hours
        except requests.exceptions.RequestException as e:
            logger.error(f"API Error validating postcode {postcode}: {e}")
            is_valid = False
        except json.JSONDecodeError as e:
            logger.error(f"API response decode error validating postcode {postcode}: {e}")
            is_valid = False

    return is_valid

def get_nearest_postcodes(postcode, limit=5, radius=1000):
    """Gets nearest postcodes for a given valid postcode."""
    if not validate_postcode(postcode):
        return []

    postcode_cleaned = postcode.strip().upper().replace(" ", "")
    cache_key = f"nearest_postcodes_{postcode_cleaned}_{limit}_{radius}"
    nearest = cache.get(cache_key)

    if nearest is None:
        try:
            # First, lookup the postcode to get its details
            lookup_response = requests.get(f"{POSTCODES_IO_BASE_URL}/postcodes/{postcode_cleaned}")
            lookup_response.raise_for_status()
            postcode_details = lookup_response.json().get("result")

            if not postcode_details:
                logger.warning(f"Could not find details for postcode: {postcode_cleaned}")
                return []

            # Now find nearest
            response = requests.get(f"{POSTCODES_IO_BASE_URL}/postcodes/{postcode_cleaned}/nearest", 
                                  params={'limit': limit, 'radius': radius})
            response.raise_for_status()
            results = response.json().get("result")
            nearest = [pc["postcode"] for pc in results if pc] if results else []
            cache.set(cache_key, nearest, timeout=3600 * 6)  # Cache for 6 hours
        except requests.exceptions.RequestException as e:
            logger.error(f"API Error getting nearest postcodes for {postcode}: {e}")
            nearest = []
        except json.JSONDecodeError as e:
            logger.error(f"API response decode error getting nearest postcodes {postcode}: {e}")
            nearest = []
        except Exception as e:
            logger.error(f"Unexpected error getting nearest postcodes for {postcode}: {e}")
            nearest = []
            
    return nearest

def get_outcode_details(outcode):
    """Gets details for an outcode from API."""
    if not outcode or not isinstance(outcode, str):
        return None

    outcode_cleaned = outcode.strip().upper()
    cache_key = f"outcode_details_{outcode_cleaned}"
    details = cache.get(cache_key)

    if details is None:
        try:
            response = requests.get(f"{POSTCODES_IO_BASE_URL}/outcodes/{outcode_cleaned}")
            response.raise_for_status()
            result_data = response.json().get("result")
            if result_data:
                details = {
                    "admin_district": result_data.get("admin_district", []),
                    "parliamentary_constituency": result_data.get("parliamentary_constituency", []),
                    "region": result_data.get("region")
                }
                cache.set(cache_key, details, timeout=3600 * 24)  # Cache for 24 hours
            else:
                details = {}
                cache.set(cache_key, details, timeout=3600)
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 404:
                logger.debug(f"Outcode {outcode_cleaned} not found via API.")
                details = {}
                cache.set(cache_key, details, timeout=3600) 
            else:
                logger.error(f"API Error getting details for outcode {outcode_cleaned}: {e}")
                details = None
        except json.JSONDecodeError as e:
            logger.error(f"API response decode error getting outcode details {outcode_cleaned}: {e}")
            details = None

    return details

# Stubs for compatibility
def add_location_to_mapping(location, outcodes):
    """Stub - static files are read-only"""
    logger.warning(f"Cannot add location to static mapping: {location}")
    return False

def refresh_postcode_mapping():
    """Stub - static files don't need refresh"""
    data = load_static_location_data()
    return len(data.get('location_to_postcodes', {}))

def get_all_unique_locations():
    """Get all unique locations from static data"""
    data = load_static_location_data()
    location_counts = data.get('location_counts', {})
    return list(location_counts.keys())

def get_postcodes_for_location(location_name):
    """Get postcodes for a location from static data"""
    if not location_name:
        return []
    
    data = load_static_location_data()
    location_to_postcodes = data.get('location_to_postcodes', {})
    
    return location_to_postcodes.get(location_name.lower(), [])