from django.core.management.base import BaseCommand
from django.db import models, transaction
from checker.models import Component
from collections import defaultdict
import json
import time
from django.urls import reverse
from urllib.parse import quote

class Command(BaseCommand):
    help = 'Pre-generate company auction links for all companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Only update companies that have changed',
        )

    def handle(self, *args, **options):
        self.stdout.write("Building company links...")
        start_time = time.time()
        
        # Get all companies with their auction data
        self.stdout.write("Fetching company auction data...")
        
        # Use raw SQL for better performance on large dataset
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT company_name, auction_name, COUNT(*) as count
                FROM checker_component
                WHERE company_name IS NOT NULL 
                AND company_name != ''
                AND auction_name IS NOT NULL
                GROUP BY company_name, auction_name
                ORDER BY company_name, auction_name
            """)
            
            companies_data = []
            for row in cursor.fetchall():
                companies_data.append({
                    'company_name': row[0],
                    'auction_name': row[1],
                    'count': row[2]
                })
        
        # Group by company
        self.stdout.write("Grouping by company...")
        companies_grouped = defaultdict(list)
        total_components = 0
        
        for item in companies_data:
            if item['auction_name']:  # Only include if has auction
                companies_grouped[item['company_name']].append({
                    'auction': item['auction_name'],
                    'count': item['count']
                })
                total_components += item['count']
        
        self.stdout.write(f"Found {len(companies_grouped)} companies with {total_components} components")
        
        # Create or get the CompanyLinks model
        from django.apps import apps
        try:
            CompanyLinks = apps.get_model('checker', 'CompanyLinks')
        except LookupError:
            self.stdout.write(self.style.ERROR("CompanyLinks model not found. Creating it..."))
            # We'll need to create this model first
            return
        
        # Build links for each company
        created_count = 0
        updated_count = 0
        batch_size = 100
        company_items = list(companies_grouped.items())
        total_companies = len(company_items)
        
        self.stdout.write(f"Building links for {total_companies} companies...")
        
        # Process in batches for better performance
        for i in range(0, total_companies, batch_size):
            batch = company_items[i:i + batch_size]
            
            with transaction.atomic():
                for company_name, auctions in batch:
                    # Build the links data
                    links_data = []
                    total_count = 0
                    
                    for auction in auctions:
                        # Build proper URL
                        search_params = f"?company={quote(company_name)}&auction={quote(auction['auction'])}"
                        links_data.append({
                            'auction': auction['auction'],
                            'count': auction['count'],
                            'url': f"/search/{search_params}"
                        })
                        total_count += auction['count']
                    
                    # Create or update the CompanyLinks entry
                    obj, created = CompanyLinks.objects.update_or_create(
                        company_name=company_name,
                        defaults={
                            'auction_links': links_data,
                            'component_count': total_count,
                            'auction_count': len(auctions)
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            
            # Progress update after each batch
            self.stdout.write(f"Processed {created_count + updated_count}/{total_companies} companies...")
        
        elapsed = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted in {elapsed:.2f}s\n"
                f"Created: {created_count} new entries\n"
                f"Updated: {updated_count} existing entries\n"
                f"Total: {len(companies_grouped)} companies"
            )
        )
        
        # Show sample output
        if CompanyLinks.objects.exists():
            sample = CompanyLinks.objects.first()
            self.stdout.write("\nSample entry:")
            self.stdout.write(f"Company: {sample.company_name}")
            self.stdout.write(f"Total components: {sample.component_count}")
            self.stdout.write(f"Auctions: {sample.auction_count}")
            if sample.auction_links:
                self.stdout.write(f"First auction: {sample.auction_links[0]['auction']} ({sample.auction_links[0]['count']} components)")