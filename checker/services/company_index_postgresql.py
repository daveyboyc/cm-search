import logging
import time
from django.db import models
from checker.models_company import Company

logger = logging.getLogger(__name__)

def get_company_links_html_postgresql(search_term):
    """
    Get HTML links for companies matching the search term using PostgreSQL.
    Replaces the Redis-based company search.
    
    Args:
        search_term (str): The search term
        
    Returns:
        list: List of HTML strings for each matching company
        int: Number of matches found
        float: Total time spent searching
    """
    start_time = time.time()
    
    if not search_term or len(search_term.strip()) < 2:
        return [], 0, time.time() - start_time
    
    # Search using the PostgreSQL Company model
    companies = Company.search_companies(search_term, limit=50)
    
    # Extract HTML for each match
    html_links = [company.search_result_html for company in companies]
    
    total_time = time.time() - start_time
    count = len(html_links)
    
    logger.info(f"PostgreSQL company search for '{search_term}': {count} results in {total_time:.4f}s")
    
    return html_links, count, total_time

def search_companies_postgresql(search_term, limit=50):
    """
    Search companies using PostgreSQL and return Company objects.
    
    Args:
        search_term (str): The search term
        limit (int): Maximum number of results
        
    Returns:
        QuerySet: Company objects matching the search
        float: Time spent searching
    """
    start_time = time.time()
    
    if not search_term or len(search_term.strip()) < 2:
        return Company.objects.none(), time.time() - start_time
    
    # Use the Company model's search method
    companies = Company.search_companies(search_term, limit=limit)
    
    search_time = time.time() - start_time
    logger.info(f"PostgreSQL company search for '{search_term}': {companies.count()} results in {search_time:.4f}s")
    
    return companies, search_time

def get_company_stats():
    """
    Get statistics about the PostgreSQL Company table.
    
    Returns:
        dict: Statistics about companies
    """
    start_time = time.time()
    
    stats = {
        'total_companies': Company.objects.count(),
        'total_components': Company.objects.aggregate(
            total=models.Sum('component_count')
        )['total'] or 0,
        'total_capacity_mw': Company.objects.aggregate(
            total=models.Sum('total_capacity_mw')
        )['total'] or 0,
        'largest_companies': list(
            Company.objects.order_by('-component_count')[:5].values(
                'name', 'component_count', 'total_capacity_mw'
            )
        ),
        'query_time': time.time() - start_time
    }
    
    logger.info(f"Company stats retrieved in {stats['query_time']:.4f}s")
    return stats