#!/usr/bin/env python
"""
Test pre-generating all company links once and storing them
"""
import os
import sys
import django
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.core.cache import cache
from collections import defaultdict

def analyze_current_approach():
    """Show the inefficiency of current approach"""
    print("CURRENT APPROACH PROBLEMS")
    print("=" * 80)
    
    # Get unique companies
    unique_companies = Component.objects.exclude(
        company_name__isnull=True
    ).values_list('company_name', flat=True).distinct()
    
    total_companies = len(unique_companies)
    print(f"\nTotal unique companies: {total_companies}")
    
    # Simulate current approach
    print("\nCurrent approach for EACH search result:")
    print("1. Get company name from component")
    print("2. Query database for all components with that company")
    print("3. Group by auction year")
    print("4. Build HTML links")
    print("5. Repeat 100x per page!")
    
    print(f"\nIf showing 100 components from 50 different companies:")
    print(f"  - Database queries: 50")
    print(f"  - Link building operations: 50")
    print(f"  - EVERY SINGLE SEARCH!")

def build_all_company_links():
    """Pre-generate all company links ONCE"""
    print("\n\nPRE-GENERATED APPROACH")
    print("=" * 80)
    
    start_time = time.time()
    company_links = {}
    
    # Get all companies and their components grouped by auction
    companies_data = Component.objects.exclude(
        company_name__isnull=True
    ).values('company_name', 'auction_name').annotate(
        count=django.db.models.Count('id')
    ).order_by('company_name', 'auction_name')
    
    # Group by company
    companies_grouped = defaultdict(list)
    for item in companies_data:
        if item['auction_name']:  # Only include if has auction
            companies_grouped[item['company_name']].append({
                'auction': item['auction_name'],
                'count': item['count']
            })
    
    # Build links for each company
    for company_name, auctions in companies_grouped.items():
        # Build the HTML links (simplified version)
        links_html = ""
        for auction in auctions:
            # In real implementation, use proper URL building
            url = f"/search/?company={company_name}&auction={auction['auction']}"
            links_html += f'<a href="{url}" class="auction-link">{auction["auction"]} ({auction["count"]})</a> '
        
        company_links[company_name] = {
            'html': links_html,
            'auction_count': len(auctions),
            'total_components': sum(a['count'] for a in auctions)
        }
    
    elapsed = time.time() - start_time
    
    print(f"Pre-generated links for {len(company_links)} companies in {elapsed:.2f}s")
    print(f"Total size: ~{len(json.dumps(company_links)) / 1024:.1f} KB")
    
    # Show sample
    sample_company = list(company_links.keys())[0]
    print(f"\nSample - {sample_company}:")
    print(f"  Auctions: {company_links[sample_company]['auction_count']}")
    print(f"  Components: {company_links[sample_company]['total_components']}")
    print(f"  HTML: {company_links[sample_company]['html'][:100]}...")
    
    return company_links

def propose_implementation():
    """Propose the implementation approach"""
    print("\n\nIMPLEMENTATION PROPOSAL")
    print("=" * 80)
    
    print("\n1. Create CompanyLink model or cache:")
    print("""
    class CompanyLink(models.Model):
        company_name = models.CharField(max_length=255, unique=True, db_index=True)
        auction_links = models.JSONField()  # Pre-built HTML or link data
        component_count = models.IntegerField()
        last_updated = models.DateTimeField(auto_now=True)
    """)
    
    print("\n2. Management command to build links:")
    print("   python manage.py build_company_links")
    print("   - Runs once after each crawl")
    print("   - Stores in database or Redis")
    print("   - Takes ~30 seconds for entire database")
    
    print("\n3. In search results:")
    print("""
    # Instead of building links for each component:
    for component in results:
        # OLD: Build links dynamically (SLOW)
        # company_links = build_company_links(component.company_name)
        
        # NEW: Just look up pre-built links (FAST)
        company_links = CompanyLink.objects.get(company_name=component.company_name)
        component.links_html = company_links.auction_links
    """)
    
    print("\n4. Update strategy:")
    print("   - After weekly incremental update: Rebuild affected companies only")
    print("   - After auction update: Full rebuild (30 seconds)")

def calculate_performance_gain():
    """Calculate the performance improvement"""
    print("\n\nPERFORMANCE GAIN CALCULATION")
    print("=" * 80)
    
    # Assumptions
    companies_per_page = 50  # Average unique companies shown per search page
    time_per_link_build = 0.01  # 10ms to build links for one company
    
    print(f"\nAssumptions:")
    print(f"  - Average unique companies per search page: {companies_per_page}")
    print(f"  - Time to build links per company: {time_per_link_build*1000:.0f}ms")
    
    print(f"\nCurrent approach (per search):")
    current_time = companies_per_page * time_per_link_build
    print(f"  - Time: {current_time*1000:.0f}ms")
    print(f"  - Database queries: {companies_per_page}")
    
    print(f"\nPre-generated approach (per search):")
    lookup_time = 0.0001  # 0.1ms to look up pre-built links
    new_time = companies_per_page * lookup_time
    print(f"  - Time: {new_time*1000:.1f}ms") 
    print(f"  - Database queries: 0 (or 1 batch)")
    
    print(f"\nImprovement: {current_time/new_time:.0f}x faster!")

if __name__ == "__main__":
    analyze_current_approach()
    company_links = build_all_company_links()
    propose_implementation()
    calculate_performance_gain()
    
    print("\n\nCONCLUSION:")
    print("Pre-generating company links would:")
    print("  ✓ Eliminate redundant database queries")
    print("  ✓ Make search results 100x faster for link building")
    print("  ✓ Work perfectly with static/weekly updated data")
    print("  ✓ Simple to implement and maintain")