"""
Search suggestions service using RapidFuzz for fuzzy string matching.
Provides "Did you mean?" functionality for search queries.
"""
import logging
from typing import List, Optional, Tuple
from rapidfuzz import fuzz, process
from django.core.cache import cache
from django.db.models import Count
from checker.models import Component
from .filter_options import get_all_technologies, get_all_companies

logger = logging.getLogger(__name__)

# Cache settings
SUGGESTIONS_CACHE_TTL = 86400  # 24 hours
MIN_SIMILARITY_SCORE = 70  # Minimum score to suggest (0-100)
MAX_SUGGESTIONS = 3  # Maximum number of suggestions to return


def get_search_dictionary() -> List[str]:
    """
    Build a dictionary of common search terms including:
    - All technologies
    - Top companies
    - Common capacity market terms
    - Common location names
    """
    cache_key = "search:dictionary:v5"
    dictionary = cache.get(cache_key)
    
    if dictionary is None:
        logger.info("Building search dictionary for suggestions")
        
        # Start with technologies
        dictionary = get_all_technologies()
        
        # Add top 100 companies
        companies = get_all_companies()[:100]
        dictionary.extend(companies)
        
        # Add common location names (top 200 most common to catch more places)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT location, COUNT(*) as component_count
                FROM checker_component 
                WHERE location IS NOT NULL AND location != ''
                GROUP BY location
                ORDER BY component_count DESC
                LIMIT 200
            """)
            locations = [row[0] for row in cursor.fetchall()]
            
        # Extract city/area names from locations (remove postcodes and details)
        location_names = []
        for location in locations:
            # Extract likely place names (before postcodes, common patterns)
            import re
            # Remove postcodes (UK format)
            location_clean = re.sub(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', '', location)
            # Remove common words like "CHP", "Road", "Avenue", etc. but keep place names
            common_words = {'chp', 'road', 'avenue', 'street', 'lane', 'close', 'drive', 'way', 'place', 'ltd', 'limited', 'farm', 'site', 'station'}
            
            # Split by common delimiters and extract meaningful parts
            parts = re.split(r'[,;]', location_clean)
            for part in parts:
                words = part.strip().split()
                for word in words:
                    word = word.strip(',').strip().lower()
                    # Include words that are likely place names
                    if (len(word) >= 4 and 
                        not word.isdigit() and 
                        word not in common_words and
                        not re.match(r'^[a-z]{1,2}\d', word)):  # Avoid postcode fragments
                        location_names.append(word)
        
        dictionary.extend(location_names)
        
        # Add common capacity market terms
        common_terms = [
            'battery', 'storage', 'gas', 'ocgt', 'ccgt', 'chp', 
            'combined heat and power', 'solar', 'wind', 'nuclear',
            'dsr', 'demand side response', 'ev charging', 'electric vehicle',
            'interconnector', 'hydro', 'pumped hydro', 'diesel',
            'coal', 'biomass', 'waste', 'landfill gas', 'sewage gas',
            'reciprocating engine', 'gas turbine', 'steam turbine',
            'flexitricity', 'limejump', 'kiwi power', 'enel x',
            'centrica', 'sse', 'edf', 'eon', 'rwe', 'drax',
            'intergen', 'uniper', 'ep uk', 'vitol', 'orsted',
            # Common location names that we definitely want to suggest
            'colindale', 'manchester', 'birmingham', 'glasgow', 'edinburgh',
            'liverpool', 'newcastle', 'cardiff', 'bristol', 'leicester',
            'london', 'peckham', 'camden', 'hackney', 'islington', 'southwark',
            'lambeth', 'wandsworth', 'tower hamlets', 'greenwich', 'lewisham',
            'leeds', 'sheffield', 'bradford', 'nottingham', 'southampton',
            'portsmouth', 'brighton', 'oxford', 'cambridge', 'reading'
        ]
        dictionary.extend(common_terms)
        
        # Remove duplicates and convert to lowercase for matching
        # Also filter out very short terms that could cause bad matches
        dictionary = list(set(term.lower() for term in dictionary if term and len(term) >= 4))
        
        cache.set(cache_key, dictionary, SUGGESTIONS_CACHE_TTL)
        logger.info(f"Cached search dictionary with {len(dictionary)} terms")
    
    return dictionary


def get_search_suggestions(query: str, max_results: int = MAX_SUGGESTIONS) -> List[Tuple[str, float]]:
    """
    Get search suggestions for a misspelled query.
    
    Args:
        query: The search query that returned no results
        max_results: Maximum number of suggestions to return
        
    Returns:
        List of tuples (suggested_term, similarity_score)
    """
    if not query or len(query) < 2:
        return []
    
    # Normalize query
    query_lower = query.lower().strip()
    
    # Check cache first (sanitize cache key for memcached compatibility)
    cache_key = f"search:suggestions:{query_lower.replace(' ', '_').replace(':', '_')}"
    cached_suggestions = cache.get(cache_key)
    if cached_suggestions is not None:
        return cached_suggestions[:max_results]
    
    # Get search dictionary
    dictionary = get_search_dictionary()
    
    # Use RapidFuzz to find best matches
    # Using WRatio which handles different word orders and partial matches well
    matches = process.extract(
        query_lower,
        dictionary,
        scorer=fuzz.WRatio,
        limit=max_results * 3  # Get extra to filter by score and length
    )
    
    # Filter by minimum score and format results
    # Also apply length-based filtering to avoid suggesting very short words for longer queries
    suggestions = []
    for match in matches:
        term, score = match[0], match[1]
        
        # Apply minimum score filter
        if score < MIN_SIMILARITY_SCORE:
            continue
            
        # For longer queries, avoid suggesting much shorter terms (prevents "coal" for "collindale")
        # But allow suggestions that are only 1-2 characters different (like "londun" -> "london")
        length_diff = abs(len(query_lower) - len(term))
        if len(query_lower) >= 8 and len(term) <= 4 and length_diff > 2:
            continue
            
        # For very long queries, prefer terms that are at least half the length
        if len(query_lower) >= 10 and len(term) < len(query_lower) / 2:
            continue
            
        suggestions.append((term, score))
    
    # Limit to max results
    suggestions = suggestions[:max_results]
    
    # Cache the suggestions
    cache.set(cache_key, suggestions, 3600)  # Cache for 1 hour
    
    return suggestions


def get_did_you_mean_suggestion(query: str) -> Optional[str]:
    """
    Get a single "Did you mean?" suggestion for a query.
    
    Args:
        query: The search query that returned no results
        
    Returns:
        The best suggestion or None if no good match found
    """
    suggestions = get_search_suggestions(query, max_results=1)
    
    if suggestions and suggestions[0][1] >= MIN_SIMILARITY_SCORE:
        # Return the suggestion with proper capitalization
        suggested_term = suggestions[0][0]
        
        # Try to find the original capitalization in our sources
        all_terms = get_all_technologies() + get_all_companies()[:100]
        for term in all_terms:
            if term.lower() == suggested_term:
                return term
        
        # If not found, return with title case
        return suggested_term.title()
    
    return None


def get_multiple_suggestions(query: str) -> List[str]:
    """
    Get multiple search suggestions for display.
    
    Args:
        query: The search query that returned no results
        
    Returns:
        List of suggested search terms
    """
    suggestions = get_search_suggestions(query)
    
    # Get proper capitalization for suggestions
    result = []
    all_terms = get_all_technologies() + get_all_companies()[:100]
    term_map = {term.lower(): term for term in all_terms}
    
    for suggestion, score in suggestions:
        # Use original capitalization if available
        proper_term = term_map.get(suggestion, suggestion.title())
        result.append(proper_term)
    
    return result


def refresh_search_dictionary():
    """Force refresh of the search dictionary cache."""
    cache.delete("search:dictionary:v1")
    dictionary = get_search_dictionary()
    logger.info(f"Search dictionary refreshed with {len(dictionary)} terms")
    return len(dictionary)