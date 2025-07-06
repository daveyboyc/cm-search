import logging
import pickle
import base64
import time
from django.core.cache import cache
from rapidfuzz import fuzz
from ..utils import normalize

logger = logging.getLogger(__name__)

# Redis keys - must match the ones in build_company_index.py
COMPANY_INDEX_KEY = "company_index_v1"
COMPANY_INDEX_UPDATE_KEY = "company_index_last_updated"

def get_company_index():
    """
    Load the company index from Redis.
    
    Returns:
        dict: The company index mapping normalized company names to data
        float: Time to load the index
        bool: Whether the index was loaded from Redis cache
    """
    start_time = time.time()
    
    # Try to get from Redis cache
    serialized_index = cache.get(COMPANY_INDEX_KEY)
    if serialized_index is None:
        logger.warning("Company index not found in Redis - attempting auto-rebuild")
        # Auto-rebuild the company index if missing
        from django.core.management import call_command
        try:
            call_command('build_company_index', '--force')
            # Try to load again after rebuild
            serialized_index = cache.get(COMPANY_INDEX_KEY)
            if serialized_index is None:
                logger.error("Failed to auto-rebuild company index")
                return {}, time.time() - start_time, False
            logger.info("Successfully auto-rebuilt company index")
        except Exception as e:
            logger.error(f"Error auto-rebuilding company index: {e}")
            return {}, time.time() - start_time, False
    
    try:
        # Deserialize the index from Redis
        company_index = pickle.loads(base64.b64decode(serialized_index))
        load_time = time.time() - start_time
        num_companies = len(company_index)
        
        logger.info(f"Loaded company index from Redis with {num_companies} companies in {load_time:.4f}s")
        return company_index, load_time, True
    except Exception as e:
        logger.error(f"Error deserializing company index from Redis: {str(e)}")
        return {}, time.time() - start_time, False

def find_companies_by_name(search_term, company_index, score_cutoff=70, limit=20):
    """
    Find companies in the index that match the search term using fuzzy matching.
    
    Args:
        search_term (str): The search term
        company_index (dict): The company index from get_company_index()
        score_cutoff (int): Minimum similarity score (0-100)
        limit (int): Maximum number of results to return
        
    Returns:
        list: Matching company data objects sorted by relevance
        float: Time to search
    """
    if not search_term or not isinstance(search_term, str) or not company_index:
        return [], 0.0
    
    start_time = time.time()
    normalized_term = normalize(search_term)
    
    # Find matches using both fuzzy matching and substring matching
    matches = []
    for norm_name, company_data in company_index.items():
        # Calculate similarity score
        fuzzy_score = fuzz.ratio(normalized_term, norm_name)
        
        # Also check for substring matches (gives higher priority)
        substring_match = normalized_term in norm_name or norm_name in normalized_term
        
        # Use fuzzy score if it meets cutoff, or boost substring matches
        if fuzzy_score >= score_cutoff:
            score = fuzzy_score
        elif substring_match and len(normalized_term) >= 4:  # Only boost substring matches for 4+ char searches
            score = 80  # Give substring matches a good score
        else:
            continue  # Skip this match
            
        # Add score to the company data for sorting
        company_with_score = company_data.copy()
        company_with_score["score"] = score
        matches.append(company_with_score)
    
    # Sort by score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Apply limit
    matches = matches[:limit]
    
    search_time = time.time() - start_time
    logger.info(f"Found {len(matches)} companies matching '{search_term}' (normalized: '{normalized_term}') in {search_time:.4f}s")
    
    return matches, search_time

def get_company_links_html(search_term):
    """
    DEPRECATED: This function now redirects to PostgreSQL-based company search.
    Use company_index_postgresql.get_company_links_html_postgresql() directly for new code.
    
    Args:
        search_term (str): The search term
        
    Returns:
        list: List of HTML strings for each matching company
        int: Number of matches found
        float: Total time spent (loading + searching)
    """
    # Redirect to PostgreSQL implementation
    from .company_index_postgresql import get_company_links_html_postgresql
    logger.info(f"Redirecting company search '{search_term}' to PostgreSQL implementation")
    return get_company_links_html_postgresql(search_term) 