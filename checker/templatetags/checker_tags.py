from django import template
import json
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
from ..utils import normalize # Import normalize function
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
import logging
import re
from urllib.parse import urlencode


register = template.Library()
logger = logging.getLogger(__name__)

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get an item from a dictionary using bracket notation."""
    return dictionary.get(key, 'N/A')

@register.filter(name='dictitem')
def dictitem(dictionary, key):
    """Get an item from a dictionary - alternative to get_item."""
    if not dictionary or not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)

@register.filter
def replace(value, arg):
    """
    Replace one string with another in a given value.
    Usage: {{ value|replace:'oldstring,newstring' }}
    Example: {{ "hello-world"|replace:'-,_' }} becomes "hello_world"
    """
    if len(arg.split(',')) != 2:
        return value
    
    old_str, new_str = arg.split(',')
    return value.replace(old_str, new_str)


@register.filter
def url_safe(value):
    """
    Make a string URL-safe by replacing spaces with underscores.
    Usage: {{ value|url_safe }}
    Example: {{ "hello world"|url_safe }} becomes "hello_world"
    """
    # First slugify to handle special characters, then replace hyphens with underscores
    from django.utils.text import slugify
    return slugify(value).replace('-', '_')


@register.filter
def cmu_count(cmu_ids):
    """
    Get CMU count from either list or dict format (for egress optimization).
    Usage: {{ location_group.cmu_ids|cmu_count }}
    """
    if not cmu_ids:
        return 0
    
    # Check if it's the new dict format with count
    if isinstance(cmu_ids, dict) and 'count' in cmu_ids:
        return cmu_ids['count']
    
    # Otherwise it's a list, return length
    if isinstance(cmu_ids, list):
        return len(cmu_ids)
    
    return 0


@register.filter
def tech_badge_class(technology):
    """
    Return the appropriate badge class for a technology.
    Usage: {{ technology|tech_badge_class }}
    """
    if not technology:
        return 'badge-unknown'
    
    tech_lower = technology.lower()
    
    # Map technology names to badge classes
    # Check for interconnector types (same logic as technology_color function)
    interconnector_types = [
        'britned', 'eleclink', 'ewic', 'greenlink', 
        'ifa', 'ifa2', 'moyle', 'nemo', 'neuconnect', 
        'nsl', 'vikinglink', 'ireland', 'france', 
        'belgium', 'norway', 'denmark', 'netherlands', 'germany'
    ]
    
    if 'interconnector' in tech_lower or 'interconnection' in tech_lower or \
       any(itype in tech_lower for itype in interconnector_types):
        return 'badge-interconnector'
    elif 'battery' in tech_lower or ('storage' in tech_lower and 'pumped' not in tech_lower):
        return 'badge-battery'
    elif 'wind' in tech_lower:
        return 'badge-wind'
    elif 'solar' in tech_lower or 'photovoltaic' in tech_lower:
        return 'badge-solar'
    elif 'gas' in tech_lower or 'ocgt' in tech_lower or 'ccgt' in tech_lower or 'reciprocating' in tech_lower or 'oil-fired' in tech_lower:
        return 'badge-gas'
    elif 'nuclear' in tech_lower:
        return 'badge-nuclear'
    elif 'hydro' in tech_lower:
        return 'badge-hydro'
    elif 'chp' in tech_lower or 'combined heat' in tech_lower:
        return 'badge-chp'
    elif 'biomass' in tech_lower or 'waste' in tech_lower:
        return 'badge-biomass'
    elif 'coal' in tech_lower:
        return 'badge-coal'
    elif 'ev charging' in tech_lower or 'ev charger' in tech_lower:
        return 'badge-ev-charging'
    elif 'dsr' in tech_lower:
        return 'badge-dsr'
    else:
        return 'badge-unknown'

@register.filter(name='slugify_for_url')
def slugify_for_url(value):
    import re
    from django.utils.text import slugify
    
    # Remove or replace invalid characters before slugifying
    value = re.sub(r'[^\w\s-]', '', value)
    return slugify(value) if value else 'unknown'

@register.filter(name='pprint')
def pretty_print(value):
    import pprint
    return pprint.pformat(value, indent=2)

@register.filter(is_safe=True)
def jsonify(value):
    """Converts a Python dict or list to a JSON string for <pre> display."""
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return str(value) # Fallback

@register.filter(name='replace_underscores')
def replace_underscores(value):
    if isinstance(value, str):
        return value.replace('_', ' ')
    return value

@register.filter(name='normalize')
def normalize_filter(value):
    from ..utils import normalize # Local import to avoid circular dependency issues
    if isinstance(value, str):
        return normalize(value)
    return value

@register.filter(name='urlencode')
def urlencode_filter(value):
    """URL encodes a string, handling spaces and special characters."""
    import urllib.parse
    return urllib.parse.quote(str(value))

@register.filter(name='format_value')
def format_value(value):
    """Formats a value for display, handling numbers, None, and strings."""
    if value is None or value == '':
        return "N/A"
    
    # Try converting to float for formatting
    try:
        float_val = float(value)
        # Check if it's effectively an integer
        if float_val == int(float_val):
            return intcomma(int(float_val))
        else:
            # Format as float with commas and reasonable precision (e.g., 2 decimal places)
            # Use f-string formatting for precision control before intcomma
            formatted_num = f"{float_val:,.2f}" 
            return formatted_num
    except (ValueError, TypeError):
        # If it's not a number, return the original value as a string
        return str(value)

@register.filter(name='shorten_auction_name')
def shorten_auction_name(value):
    """Shortens auction names like '2024-25 (T-4) Four Year Ahead Capacity Auction' to '2024-25 (T-4)'."""
    if not isinstance(value, str):
        return value
    
    # Regex to capture the year range and auction type (T-1, T-3, T-4, TR)
    # Allows for year formats like 2024/25, 2024-25, 2024
    # Allows for T-1, T1, T-3, T3, T-4, T4, TR
    match = re.match(r"^\s*(\d{4}[/-]?\d{2,4}|\d{4})\s*\((T[-]?\d|TR)\).*", value, re.IGNORECASE)
    
    if match:
        year_part = match.group(1)
        type_part = match.group(2).upper().replace('-', '') # Normalize to T1, T3, T4, TR
        # Re-add hyphen for T-1, T-3, T-4
        if type_part in ['T1', 'T3', 'T4']:
            type_part = f"T-{type_part[1]}"
            
        return f"{year_part} ({type_part})"
    else:
        # If no match, return the original string (or a truncated version)
        return value # Or perhaps value[:30] + '...' if you want to truncate unknowns

@register.filter(name='strip_prefix')
def strip_prefix(value, prefix):
    """Removes a specific prefix from a string if it exists."""
    if isinstance(value, str) and value.startswith(prefix):
        return value[len(prefix):]
    return value

@register.filter(name='group_by_location')
def group_by_location(components):
    """
    Groups components by location and description, preserving unique CMU IDs and delivery years.
    
    Returns a list of grouped components, where each group has:
    - location: The shared location
    - description: The shared description
    - cmu_ids: List of unique CMU IDs
    - auction_names: List of unique auction names
    - auction_to_components: Mapping of auction names to component IDs
    - active_status: Whether any components in the group are from 2024-25 or later
    - first_component: The first component in the group (for reference)
    - count: Number of components in the group
    """
    if not components:
        return []
    
    def normalize_location(loc):
        """Normalize location for consistent grouping"""
        if not loc:
            return ""
        # Convert to lowercase and strip whitespace
        norm = loc.lower().strip()
        # Remove common punctuation
        norm = re.sub(r'[,\.\-_\/\\]', ' ', norm)
        # Remove extra whitespace
        norm = re.sub(r'\s+', ' ', norm)
        # Handle special cases
        if "energy centre" in norm and "mosley" in norm:
            return "energy centre lower mosley street"
        return norm
    
    def is_auction_year_active(auction_name):
        """Check if an auction year is 2024-25 or later"""
        if not auction_name:
            return False
        
        # Extract year from auction name using regex
        year_match = re.search(r'(\d{4})[-/]?(\d{2,4})', auction_name)
        if year_match:
            start_year = year_match.group(1)
            try:
                # Convert to integer for comparison
                year_int = int(start_year)
                # Active if 2024 or later
                return year_int >= 2024
            except ValueError:
                return False
        return False
    
    groups = {}
    
    for comp in components:
        # Extract key fields
        location = comp.get('location', '')
        description = comp.get('description', '')
        cmu_id = comp.get('cmu_id', '')
        auction_name = comp.get('auction_name', '')
        component_id = comp.get('id')  # Get component ID for linking
        
        # Create normalized keys for grouping
        norm_location = normalize_location(location)
        
        # Create a group key
        group_key = (norm_location, description)
        
        if group_key not in groups:
            groups[group_key] = {
                'location': location,  # Keep original formatting
                'description': description,
                'cmu_ids': set(),
                'auction_names': set(),
                'auction_to_components': {},  # Map auction names to component IDs
                'active_status': False,  # Initialize as inactive
                'components': [],
                'first_component': comp  # Store first component
            }
        
        if cmu_id:
            groups[group_key]['cmu_ids'].add(cmu_id)
        
        if auction_name:
            groups[group_key]['auction_names'].add(auction_name)
            
            # Check if this auction makes the group active
            if is_auction_year_active(auction_name):
                groups[group_key]['active_status'] = True
            
            # Store the component ID for this auction name
            if component_id and auction_name:
                if auction_name not in groups[group_key]['auction_to_components']:
                    groups[group_key]['auction_to_components'][auction_name] = []
                groups[group_key]['auction_to_components'][auction_name].append(component_id)
        
        groups[group_key]['components'].append(comp)
    
    # Convert to list and add count
    result = []
    for key, group in groups.items():
        group['count'] = len(group['components'])
        group['cmu_ids'] = list(group['cmu_ids'])
        
        # Sort auction names by year in descending order (newest first)
        def extract_year(auction_name):
            year_match = re.search(r'(\d{4})[-/]?(\d{2,4})', auction_name)
            if year_match:
                try:
                    return int(year_match.group(1))
                except ValueError:
                    return 0
            return 0
        
        # Convert to list and sort in descending order
        auction_names_list = list(group['auction_names'])
        auction_names_list.sort(key=extract_year, reverse=True)
        group['auction_names'] = auction_names_list
        
        result.append(group)
        
    # Sort the result list alphabetically by location if requested via query params
    request = None
    try:
        from django.core.handlers.wsgi import WSGIRequest
        import inspect
        for frame in inspect.stack():
            if 'request' in frame.frame.f_locals:
                possible_request = frame.frame.f_locals['request']
                if isinstance(possible_request, WSGIRequest):
                    request = possible_request
                    break
        
        if request and request.GET.get('sort_by') == 'location':
            sort_order = request.GET.get('sort_order', 'asc').lower()
            logger.info(f"Applying additional location sort to grouped results ({sort_order})")
            
            # Sort the groups by location (safely handling None values)
            reverse_sort = (sort_order == 'desc')
            # Use a lambda that safely handles None or empty location values
            result.sort(key=lambda x: (x['location'] or '').lower(), reverse=reverse_sort)
    except Exception as e:
        logger.error(f"Error applying location sort to grouped results: {e}")
    
    return result

@register.filter(name='is_dict')
def is_dict(value):
    """Check if a value is a dictionary."""
    return isinstance(value, dict)

@register.filter(name='is_list')
def is_list(value):
    """Check if a value is a list."""
    return isinstance(value, list)

@register.filter(name='unique_with_counts')
def unique_with_counts(descriptions):
    """
    Take a list of descriptions and return unique descriptions with their counts.
    Returns a list of tuples: [(description, count), ...]
    """
    if not descriptions or not isinstance(descriptions, list):
        return []
    
    from collections import Counter
    desc_counts = Counter(descriptions)
    
    # Return as list of tuples, sorted by count (descending) then by description
    return sorted(desc_counts.items(), key=lambda x: (-x[1], x[0]))

@register.filter(name='sort_auction_years_desc')
def sort_auction_years_desc(auction_years):
    """
    Sort auction years in descending order (newest first).
    Handles formats like '2024-25 (T-4) Four Year Ahead Capacity Auction'
    """
    if not auction_years or not isinstance(auction_years, list):
        return []
    
    # Sort by extracting the year from each string
    def get_year_key(year_str):
        import re
        match = re.search(r'(\d{4})-\d{2}', year_str)
        if match:
            return int(match.group(1))
        return 0
    
    return sorted(auction_years, key=get_year_key, reverse=True)

@register.filter(name='is_active_year')
def is_active_year(auction_years):
    """
    Check if any auction year is 2024 or later (active).
    Can handle dict (from LocationGroup), list, or single string.
    Returns True if active, False if inactive.
    """
    import re
    
    # Handle dict (LocationGroup auction_years format: {"2024-25": 1, "2025-26": 2})
    if isinstance(auction_years, dict):
        for year_str in auction_years.keys():
            match = re.search(r'(\d{4})', year_str)
            if match:
                year = int(match.group(1))
                if year >= 2024:
                    return True
        return False
    
    # Handle single year string
    if isinstance(auction_years, str):
        match = re.search(r'(\d{4})', auction_years)
        if match:
            year = int(match.group(1))
            return year >= 2024
        return False
    
    # Handle list of years
    if not auction_years or not isinstance(auction_years, list):
        return False
    
    for year_str in auction_years:
        # Extract the first year from patterns like "2024-25 (T-4)" or "2024/25"
        match = re.search(r'(\d{4})', year_str)
        if match:
            year = int(match.group(1))
            if year >= 2024:
                return True
    return False

@register.filter(name='technology_color')
def technology_color(technology):
    """
    Get the hex color for a technology type matching the map colors.
    Returns the color code used in the map visualization.
    """
    if not technology:
        return '#757575'  # Unknown grey
    
    # Technology color mapping - aligned with map
    tech_colors = {
        'Gas': '#ff5252',                # Red
        'DSR': '#f57c00',                # Orange
        'EV Charging': '#e91e63',        # Pink
        'Nuclear': '#8d6e63',            # Brown
        'CHP': '#5c6bc0',                # Indigo
        'Solar': '#fdd835',              # Yellow
        'Wind': '#29b6f6',               # Light Blue
        'Battery': '#4caf50',            # Green
        'Biomass': '#8bc34a',            # Light Green
        'Hydro': '#0097a7',              # Teal
        'Pumped Hydro': '#006064',       # Dark Teal
        'Interconnector': '#9c27b0',     # Purple
        'Coal': '#424242',               # Dark Grey
        'Unknown': '#757575'             # Grey
    }
    
    # Determine category (same logic as map)
    lower_tech = technology.lower()
    
    # Interconnector types
    interconnector_types = [
        'britned', 'eleclink', 'ewic', 'greenlink', 
        'ifa', 'ifa2', 'moyle', 'nemo', 'neuconnect', 
        'nsl', 'vikinglink', 'ireland', 'france', 
        'belgium', 'norway', 'denmark', 'netherlands', 'germany'
    ]
    
    category = 'Unknown'
    
    if 'interconnector' in lower_tech or 'interconnection' in lower_tech or \
       any(itype in lower_tech for itype in interconnector_types):
        category = 'Interconnector'
    elif 'battery' in lower_tech or ('storage' in lower_tech and 'pumped' not in lower_tech):
        category = 'Battery'
    elif 'wind' in lower_tech:
        category = 'Wind'
    elif 'solar' in lower_tech or 'photovoltaic' in lower_tech:
        category = 'Solar'
    elif any(term in lower_tech for term in ['gas', 'ocgt', 'ccgt', 'reciprocating', 'engines', 'oil-fired']):
        category = 'Gas'
    elif 'nuclear' in lower_tech:
        category = 'Nuclear'
    elif 'hydro' in lower_tech:
        category = 'Hydro'
    elif 'chp' in lower_tech or 'combined heat' in lower_tech:
        category = 'CHP'
    elif 'biomass' in lower_tech or 'waste' in lower_tech:
        category = 'Biomass'
    elif 'coal' in lower_tech:
        category = 'Coal'
    elif 'ev charging' in lower_tech or 'ev charger' in lower_tech:
        category = 'EV Charging'
    elif 'pumped' in lower_tech and 'hydro' in lower_tech:
        category = 'Pumped Hydro'
    elif 'dsr' in lower_tech:
        category = 'DSR'
    
    return tech_colors.get(category, '#757575')


@register.filter(name='clean_location')
def clean_location(value):
    """
    Clean up location display by removing duplicate lines.
    Usage: {{ location_group.location|clean_location }}
    """
    if not value:
        return value
    
    # Split by newlines and remove duplicates while preserving order
    lines = value.split('\n')
    seen = set()
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            cleaned_lines.append(line)
    
    # Join with a space instead of newlines for cleaner display
    return ' '.join(cleaned_lines)


@register.simple_tag(takes_context=True)
def build_filter_params(context, exclude_param=None):
    """
    Build URL parameters for filter bar, excluding one parameter.
    Usage: {% build_filter_params exclude_param='status' %}
    """
    request = context['request']
    params = {}
    
    # Core parameters to preserve
    preserve_params = [
        'q', 'sort_by', 'sort_order', 'per_page', 'page',
        'status', 'auction', 'technology', 'company'
    ]
    
    for param in preserve_params:
        if param != exclude_param and param in request.GET:
            value = request.GET.get(param)
            if value:
                params[param] = value
    
    # Remove the excluded parameter entirely and reset page to 1 when filtering
    if exclude_param and exclude_param != 'page':
        params.pop('page', None)  # Reset to page 1 when applying filters
    
    return urlencode(params)