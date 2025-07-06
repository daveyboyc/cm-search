"""
Management command to rename Flexitricity locations to include ASDA store names.
"""
from django.core.management.base import BaseCommand
from checker.models import LocationGroup, Component
from django.db.models import Q


class Command(BaseCommand):
    help = 'Rename Flexitricity locations to include ASDA store names'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of locations to process'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        
        self.stdout.write("=== RENAMING FLEXITRICITY LOCATIONS WITH ASDA STORE NAMES ===")
        
        # Find Flexitricity LocationGroups that have ASDA business information
        asda_locations = LocationGroup.objects.filter(
            companies__icontains='flexitricity',
            representative_component__places_api_business_name__icontains='asda'
        ).select_related('representative_component')
        
        if options['limit']:
            asda_locations = asda_locations[:options['limit']]
        
        self.stdout.write(f"Found {asda_locations.count()} Flexitricity locations with ASDA stores")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        renamed_count = 0
        
        for location_group in asda_locations:
            rep_comp = location_group.representative_component
            if not rep_comp or not rep_comp.places_api_business_name:
                continue
            
            old_location = location_group.location
            asda_name = rep_comp.places_api_business_name
            
            # Extract ASDA store name (e.g., "Asda Sutton Superstore" -> "Asda Sutton")
            asda_clean = self.clean_asda_name(asda_name)
            
            # Create new location name
            # If location already contains ASDA, skip
            if 'asda' in old_location.lower():
                self.stdout.write(f"SKIP: {old_location} (already contains ASDA)")
                continue
            
            # Extract postcode from location
            postcode = rep_comp.full_postcode or ""
            
            # Create new location format: "ASDA Store Name, Original Location"
            new_location = f"{asda_clean}, {old_location}"
            
            # Ensure it's not too long (database field limit)
            if len(new_location) > 255:
                # Try shorter format
                new_location = f"{asda_clean}, {self.shorten_location(old_location, postcode)}"
                if len(new_location) > 255:
                    new_location = new_location[:252] + "..."
            
            self.stdout.write(f"\n--- LocationGroup {location_group.id} ---")
            self.stdout.write(f"OLD: {old_location}")
            self.stdout.write(f"NEW: {new_location}")
            self.stdout.write(f"ASDA: {asda_name}")
            
            if not self.dry_run:
                # Update the LocationGroup
                location_group.location = new_location
                location_group.save()
                
                # Update all Components at this location
                updated_components = Component.objects.filter(
                    location=old_location
                ).update(location=new_location)
                
                self.stdout.write(f"✅ Updated LocationGroup and {updated_components} components")
                renamed_count += 1
            else:
                self.stdout.write("DRY RUN: Would update LocationGroup and components")
        
        if not self.dry_run:
            self.stdout.write(f"\n🎯 COMPLETE: Renamed {renamed_count} Flexitricity locations with ASDA store names")
        else:
            self.stdout.write(f"\nDRY RUN COMPLETE: Would rename {len(asda_locations)} locations")

    def clean_asda_name(self, asda_name):
        """Clean ASDA store name for location display"""
        if not asda_name:
            return "ASDA"
        
        # Remove common suffixes to keep it concise
        name = asda_name.replace("Superstore", "").replace("Supercentre", "").replace("Supermarket", "")
        name = name.replace("Store", "").strip()
        
        # Remove trailing comma if present
        if name.endswith(","):
            name = name[:-1].strip()
        
        return name or "ASDA"

    def shorten_location(self, location, postcode):
        """Shorten location to fit within character limits"""
        # If location has a postcode at the end, we can use that
        if postcode and postcode in location:
            # Extract the part before the postcode
            parts = location.split(postcode)
            if len(parts) > 1:
                address_part = parts[0].strip().rstrip(',').strip()
                return f"{address_part}, {postcode}"
        
        # Otherwise, truncate if too long
        if len(location) > 150:
            return location[:147] + "..."
        
        return location