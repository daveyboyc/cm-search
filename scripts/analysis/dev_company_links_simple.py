#!/usr/bin/env python
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component, CompanyLinks
from django.db.models import Count
import time

print("Testing company links generation...")

# Test with just a few companies first
test_companies = ['VITAL ENERGI SOLUTIONS LIMITED', 'FLEXITRICITY LIMITED', 'OCTOPUS ENERGY LIMITED']

for company_name in test_companies:
    print(f"\nProcessing: {company_name}")
    
    # Get auction data for this company
    auction_data = Component.objects.filter(
        company_name=company_name
    ).exclude(
        auction_name__isnull=True
    ).values('auction_name').annotate(
        count=Count('id')
    ).order_by('auction_name')
    
    if auction_data:
        links_data = []
        total_count = 0
        
        for auction in auction_data:
            links_data.append({
                'auction': auction['auction_name'],
                'count': auction['count'],
                'url': f"/search/?company={company_name}&auction={auction['auction_name']}"
            })
            total_count += auction['count']
        
        # Create or update
        obj, created = CompanyLinks.objects.update_or_create(
            company_name=company_name,
            defaults={
                'auction_links': links_data,
                'component_count': total_count,
                'auction_count': len(links_data)
            }
        )
        
        action = "Created" if created else "Updated"
        print(f"  {action}: {obj.auction_count} auctions, {obj.component_count} components")
        
        # Show sample HTML
        print(f"  Sample HTML: {obj.get_links_html()[:100]}...")

# Check total
print(f"\nTotal CompanyLinks in database: {CompanyLinks.objects.count()}")