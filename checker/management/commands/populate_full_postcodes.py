import re
import logging
from django.core.management.base import BaseCommand
from checker.models import Component

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates full_postcode field in the Component model from location data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of components to process',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if full_postcode is already populated',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        force = options.get('force')
        
        # Improved UK postcode regex pattern to match full postcodes
        # This pattern matches complete UK postcodes with optional space
        postcode_pattern = r'([A-Za-z]{1,2}[0-9][A-Za-z0-9]?\s*[0-9][A-Za-z]{2})'
        
        # Get components to process
        components_query = Component.objects.all()
        
        # Filter to only process records without full_postcode (unless force=True)
        if not force:
            components_query = components_query.filter(full_postcode__isnull=True)
        
        # Apply limit if provided
        if limit:
            components_query = components_query[:limit]
        
        # Count total to process
        total = components_query.count()
        self.stdout.write(f"Processing {total} components for full postcode extraction...")
        
        # Track progress
        processed = 0
        updated = 0
        
        # Process in batches for better performance
        batch_size = 1000
        updates_to_make = []
        
        # Process each component
        for component in components_query.iterator():
            location = component.location or ""
            
            # Extract full postcode using regex
            postcode_match = re.search(postcode_pattern, location, re.IGNORECASE)
            full_postcode = None
            
            if postcode_match:
                # Get the full postcode and normalize it
                full_postcode = postcode_match.group(1).strip().upper()
                
                # Ensure proper spacing in postcode (add space if missing)
                if ' ' not in full_postcode and len(full_postcode) >= 5:
                    # Insert space before the last 3 characters
                    full_postcode = full_postcode[:-3] + ' ' + full_postcode[-3:]
                
                # Validate the postcode format
                if re.match(r'^[A-Z]{1,2}[0-9][A-Z0-9]?\s[0-9][A-Z]{2}$', full_postcode):
                    # Add to batch update list
                    component.full_postcode = full_postcode
                    updates_to_make.append(component)
                    updated += 1
                    
                    # Log a few examples for verification
                    if updated <= 10:
                        self.stdout.write(f"  Example: {location[:50]}... -> {full_postcode}")
            
            processed += 1
            
            # Process batch updates
            if len(updates_to_make) >= batch_size:
                Component.objects.bulk_update(updates_to_make, ['full_postcode'])
                updates_to_make = []
            
            # Show progress
            if processed % 1000 == 0:
                self.stdout.write(f"Processed {processed}/{total} components, updated {updated}")
        
        # Process any remaining updates
        if updates_to_make:
            Component.objects.bulk_update(updates_to_make, ['full_postcode'])
        
        self.stdout.write(self.style.SUCCESS(f"Completed! Processed {processed} components, updated {updated} with full postcodes"))
        
        # Show some statistics
        total_with_postcodes = Component.objects.filter(full_postcode__isnull=False).count()
        total_components = Component.objects.count()
        self.stdout.write(f"Total components with full postcodes: {total_with_postcodes}/{total_components}")