from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import Count, Sum, Min, Max, Q
from checker.models import Component, LocationGroup
from collections import defaultdict
import json
import time

class Command(BaseCommand):
    help = 'Build LocationGroup records from existing components'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing LocationGroup records before building',
        )
        parser.add_argument(
            '--test',
            type=str,
            help='Test with a specific location name',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of locations to process',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        
        if options['clear']:
            self.stdout.write("Clearing existing LocationGroup records...")
            LocationGroup.objects.all().delete()
        
        if options['test']:
            # Test mode - process only one location
            self.process_single_location(options['test'])
            return
        
        self.stdout.write("Building LocationGroup records...")
        
        # Get all unique locations with valid data
        locations = list(Component.objects.exclude(
            Q(location__isnull=True) |
            Q(location='') |
            Q(location='None') |
            Q(location='N/A') |
            Q(location='NA') |
            Q(location__icontains='TBC') |
            Q(location__icontains='to be confirmed')
        ).values_list('location', flat=True).distinct())
        
        # Apply limit if specified
        if options.get('limit'):
            locations = locations[:options['limit']]
        
        total_locations = len(locations)
        self.stdout.write(f"Found {total_locations} unique valid locations")
        
        created_count = 0
        updated_count = 0
        
        # Process in batches
        batch_size = 100
        for i in range(0, total_locations, batch_size):
            batch = locations[i:i + batch_size]
            
            with transaction.atomic():
                for location in batch:
                    result = self.process_location(location)
                    if result == 'created':
                        created_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    
                    if (created_count + updated_count) % 10 == 0:
                        self.stdout.write(f"Processed {created_count + updated_count}/{total_locations} locations...")
        
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted in {elapsed:.2f}s\n"
                f"Created: {created_count} new LocationGroups\n"
                f"Updated: {updated_count} existing LocationGroups\n"
                f"Total: {created_count + updated_count} locations"
            )
        )

    def process_single_location(self, location_name):
        """Process a single location for testing"""
        self.stdout.write(f"\nTesting with location: {location_name}")
        result = self.process_location(location_name)
        
        # Show the created/updated LocationGroup
        try:
            lg = LocationGroup.objects.get(location=location_name)
            self.stdout.write(f"\nLocationGroup: {lg}")
            self.stdout.write(f"Components: {lg.component_count}")
            self.stdout.write(f"Descriptions: {json.dumps(lg.descriptions, indent=2)}")
            self.stdout.write(f"Technologies: {json.dumps(lg.technologies, indent=2)}")
            self.stdout.write(f"Companies: {json.dumps(lg.companies, indent=2)}")
            self.stdout.write(f"Auction years: {json.dumps(lg.auction_years, indent=2)}")
            self.stdout.write(f"Normalized capacity: {lg.normalized_capacity_mw:.2f} MW")
        except LocationGroup.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Failed to create/update LocationGroup"))

    def process_location(self, location):
        """Process a single location and create/update LocationGroup"""
        # Get all components at this location
        components = Component.objects.filter(location=location)
        
        if not components.exists():
            return None
        
        # Aggregate data
        component_count = components.count()
        
        # Get unique descriptions - ONLY STORE FIRST 3 FOR DISPLAY
        descriptions = list(components.values_list('description', flat=True).distinct())
        descriptions = [d for d in descriptions if d]  # Remove None/empty
        descriptions = descriptions[:3]  # Only store what's displayed in template
        
        # Count by technology
        tech_counts = components.values('technology').annotate(
            count=Count('id')
        ).order_by('-count')
        technologies = {t['technology']: t['count'] for t in tech_counts if t['technology']}
        
        # Count by company
        company_counts = components.values('company_name').annotate(
            count=Count('id')
        ).order_by('-count')
        companies = {c['company_name']: c['count'] for c in company_counts if c['company_name']}
        
        # Get unique auction years - ONLY STORE FIRST 5 FOR EGRESS REDUCTION
        auction_years = list(components.values_list('auction_name', flat=True).distinct())
        auction_years = [a for a in auction_years if a]
        # Sort auction years descending (newest first)
        auction_years.sort(reverse=True)
        auction_years = auction_years[:5]  # Only store 5 most recent (template shows 3)
        
        # Get unique CMU IDs - STORE ALL FOR FULL SEARCHABILITY
        all_cmu_ids = list(set(components.values_list('cmu_id', flat=True)))
        all_cmu_ids = [c for c in all_cmu_ids if c]
        all_cmu_ids.sort()  # Sort alphabetically
        
        # Store as list (was dict with samples, but that made most CMUs unsearchable)
        cmu_ids = all_cmu_ids
        
        # Calculate capacity
        total_capacity = components.aggregate(Sum('derated_capacity_mw'))['derated_capacity_mw__sum'] or 0.0
        
        # For now, displayed = normalized. We'll handle aggregation later
        displayed_capacity = total_capacity
        normalized_capacity = total_capacity
        
        # Determine capacity confidence
        components_with_capacity = components.filter(derated_capacity_mw__isnull=False).count()
        if components_with_capacity == 0:
            capacity_confidence = 'none'
        elif components_with_capacity == component_count:
            capacity_confidence = 'high'
        elif components_with_capacity >= component_count * 0.5:
            capacity_confidence = 'medium'
        else:
            capacity_confidence = 'low'
        
        # Determine active status - True if any component has auction year 2024-25 or later
        is_active = False
        for auction_year in auction_years:
            if auction_year and any(year in auction_year for year in ['2024-25', '2025-26', '2026-27', '2027-28', '2028-29', '2029-30']):
                is_active = True
                break
        
        # Get representative component (one with most data)
        rep_component = components.exclude(
            Q(latitude__isnull=True) | Q(longitude__isnull=True)
        ).first() or components.first()
        
        # Create or update LocationGroup
        location_group, created = LocationGroup.objects.update_or_create(
            location=location,
            defaults={
                'component_count': component_count,
                'displayed_capacity_mw': displayed_capacity,
                'normalized_capacity_mw': normalized_capacity,
                'capacity_confidence': capacity_confidence,
                'capacity_source': 'derated_capacity_mw',
                'auction_years': auction_years,
                'technologies': technologies,
                'companies': companies,
                'descriptions': descriptions,
                'cmu_ids': cmu_ids,
                'is_active': is_active,  # ADD THIS!
                'representative_component': rep_component,
                'latitude': rep_component.latitude if rep_component else None,
                'longitude': rep_component.longitude if rep_component else None,
                'county': rep_component.county if rep_component else None,
                'outward_code': rep_component.outward_code if rep_component else None,
            }
        )
        
        return 'created' if created else 'updated'
    
    def process_single_location(self, location):
        """Process a single location for testing"""
        self.stdout.write(f"Testing with location: {location}")
        
        # Check if location exists
        components = Component.objects.filter(location=location)
        if not components.exists():
            self.stdout.write(f"No components found for location: {location}")
            return
        
        self.stdout.write(f"Found {components.count()} components at this location")
        
        try:
            result = self.process_location(location)
            if result == 'created':
                self.stdout.write(self.style.SUCCESS(f"✓ Created LocationGroup for: {location}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ Updated LocationGroup for: {location}"))
            
            # Show details
            location_group = LocationGroup.objects.get(location=location)
            self.stdout.write(f"\nLocationGroup details:")
            self.stdout.write(f"  - Component count: {location_group.component_count}")
            self.stdout.write(f"  - Descriptions: {location_group.descriptions}")
            self.stdout.write(f"  - Technologies: {location_group.technologies}")
            self.stdout.write(f"  - Companies: {location_group.companies}")
            self.stdout.write(f"  - Auction years: {location_group.auction_years}")
            self.stdout.write(f"  - Capacity: {location_group.get_display_capacity()}")
            
        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f"Failed to create/update LocationGroup"))
            self.stdout.write(f"Error: {str(e)}")
            self.stdout.write(traceback.format_exc())