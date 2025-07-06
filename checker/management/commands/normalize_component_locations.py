"""
Management command to normalize all component locations in the database
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from checker.models import Component
import re

class Command(BaseCommand):
    help = 'Normalize all component locations to fix spacing inconsistencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def normalize_location(self, location):
        """Normalize location string"""
        if not location:
            return location
        
        # Strip and replace multiple spaces with single space
        location = re.sub(r'\s+', ' ', str(location).strip())
        
        # Fix UK postcode spacing (e.g., "KA1  3TN" -> "KA1 3TN")
        location = re.sub(r'([A-Z]{1,2}\d{1,2}[A-Z]?)\s+(\d[A-Z]{2})', r'\1 \2', location)
        
        return location

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write("Analyzing component locations...")
        
        # Find locations that need normalization
        components_to_update = []
        location_changes = {}
        
        for component in Component.objects.all():
            normalized = self.normalize_location(component.location)
            if normalized != component.location:
                components_to_update.append(component)
                if component.location not in location_changes:
                    location_changes[component.location] = normalized
        
        if not components_to_update:
            self.stdout.write(self.style.SUCCESS("No locations need normalization!"))
            return
        
        self.stdout.write(f"\nFound {len(components_to_update)} components to update")
        self.stdout.write(f"Affecting {len(location_changes)} unique location strings\n")
        
        # Show some examples
        self.stdout.write("Sample changes:")
        for old, new in list(location_changes.items())[:10]:
            self.stdout.write(f"  '{old}' -> '{new}'")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\nDRY RUN: Would update {len(components_to_update)} components"
            ))
            return
        
        # Perform the update
        self.stdout.write("\nUpdating components...")
        
        with transaction.atomic():
            updated = 0
            for component in components_to_update:
                component.location = self.normalize_location(component.location)
                component.save(update_fields=['location'])
                updated += 1
                
                if updated % 100 == 0:
                    self.stdout.write(f"  Updated {updated}/{len(components_to_update)} components...")
        
        self.stdout.write(self.style.SUCCESS(
            f"\nSuccessfully normalized {updated} component locations"
        ))
        self.stdout.write("\nNOTE: You should now rebuild LocationGroups with:")
        self.stdout.write("  python manage.py build_location_groups")