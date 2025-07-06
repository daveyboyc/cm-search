"""
Use pre-built CompanyLinks from database for fast company search
"""
import logging
import time
from django.db.models import Q
from ..models import CompanyLinks
from ..utils import normalize

logger = logging.getLogger(__name__)

def get_company_links_for_search(search_term, limit=20):
    """
    Get company links for search results using pre-built CompanyLinks table.
    
    Args:
        search_term (str): The search term
        limit (int): Maximum number of results
        
    Returns:
        list: List of dicts with 'html' and 'cmu_ids' keys
        int: Number of matches found  
        float: Time taken
    """
    start_time = time.time()
    
    try:
        # Simple case-insensitive search on company name
        matches = CompanyLinks.objects.filter(
            company_name__icontains=search_term
        ).order_by('-component_count')[:limit]
        
        results = []
        for company_link in matches:
            # Build HTML similar to what _build_search_results does
            normalized_id = normalize(company_link.company_name)
            company_url = f'/company-list/{normalized_id}/'
            
            html = f"""
            <div>
                <strong><a href="{company_url}">{company_link.company_name}</a></strong>
                <div class="mt-1 mb-1"><span class="text-muted">{company_link.auction_count} auctions</span></div>
                <div>{company_link.component_count} components</div>
            </div>
            """
            
            # Extract CMU IDs from auction_links if needed
            cmu_ids = []
            
            results.append({
                'html': html,
                'cmu_ids': cmu_ids
            })
        
        elapsed = time.time() - start_time
        logger.info(f"Found {len(results)} companies matching '{search_term}' in {elapsed:.3f}s using CompanyLinks")
        
        return results, len(results), elapsed
        
    except Exception as e:
        logger.error(f"Error searching CompanyLinks: {e}")
        return [], 0, time.time() - start_time