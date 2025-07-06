from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import Count, Sum, Min, Max, Q
from checker.models import Component, LocationGroup
import time

class Command(BaseCommand):
    help = 'Build LocationGroup records incrementally, skipping existing ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=int,
            default=500,
            help='Number of locations to process in this run (default: 500)',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        batch_size = options['batch']
        
        self.stdout.write("Building LocationGroup records incrementally...")
        
        # Get existing locations that already have LocationGroups
        existing_locations = set(LocationGroup.objects.values_list('location', flat=True))
        self.stdout.write(f"Found {len(existing_locations)} existing LocationGroups")
        
        # Get all unique locations with valid data that don't have LocationGroups yet
        all_locations_query = Component.objects.exclude(
            Q(location__isnull=True) |
            Q(location='') |
            Q(location='None') |
            Q(location='N/A') |
            Q(location='NA') |
            Q(location__icontains='TBC') |
            Q(location__icontains='to be confirmed')
        ).values_list('location', flat=True).distinct()
        
        # Filter out existing locations and limit to batch size
        locations_to_process = []
        for location in all_locations_query:
            if location not in existing_locations:
                locations_to_process.append(location)
                if len(locations_to_process) >= batch_size:
                    break
        
        if not locations_to_process:
            self.stdout.write(self.style.SUCCESS("All locations already have LocationGroups!"))
            return
        
        self.stdout.write(f"Processing {len(locations_to_process)} new locations...")
        
        created_count = 0
        
        # Process in smaller batches for transactions
        transaction_batch_size = 50
        for i in range(0, len(locations_to_process), transaction_batch_size):
            batch = locations_to_process[i:i + transaction_batch_size]
            
            with transaction.atomic():
                for location in batch:
                    if self.process_location(location):
                        created_count += 1
                    
                    if created_count % 10 == 0:
                        self.stdout.write(f"Created {created_count} LocationGroups...")
        
        # Final statistics
        new_total = LocationGroup.objects.count()
        total_components_covered = sum(LocationGroup.objects.values_list('component_count', flat=True))
        total_components = Component.objects.count()
        coverage = (total_components_covered / total_components * 100) if total_components > 0 else 0
        
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted in {elapsed:.2f}s\n"
                f"Created: {created_count} new LocationGroups\n"
                f"Total LocationGroups: {new_total}\n"
                f"Component coverage: {coverage:.1f}%"
            )
        )
        
        if coverage >= 80:
            self.stdout.write(self.style.SUCCESS("🎉 LocationGroups are now ACTIVE! (80% coverage reached)"))
        else:
            self.stdout.write(f"Need {80 - coverage:.1f}% more coverage to activate LocationGroups")

    def process_location(self, location):
        """Process a single location and create LocationGroup"""
        # Double-check if LocationGroup already exists (in case of race conditions)
        if LocationGroup.objects.filter(location=location).exists():
            return False
            
        # Get all components at this location
        components = Component.objects.filter(location=location)
        
        if not components.exists():
            return False
        
        # Aggregate data
        component_count = components.count()
        
        # Get unique descriptions
        descriptions = list(components.values_list('description', flat=True).distinct())
        descriptions = [d for d in descriptions if d][:5]  # Limit to 5 for JSON field
        
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
        
        # Get unique auction years
        auction_years = list(components.values_list('auction_name', flat=True).distinct())
        auction_years = [a for a in auction_years if a]
        auction_years.sort(reverse=True)  # Newest first
        
        # Determine if active (any auction year >= 2024-25)
        is_active = False
        for year_str in auction_years:
            import re
            # Match auction year format like "2024-25" and extract the first year
            match = re.search(r'(\d{4})-(\d{2})', str(year_str))
            if match:
                first_year = int(match.group(1))
                # Active if 2024-25 or later (first year >= 2024)
                if first_year >= 2024:
                    is_active = True
                    break
            else:
                # Fallback for simple year format
                simple_match = re.search(r'(\d{4})', str(year_str))
                if simple_match and int(simple_match.group(1)) >= 2024:
                    is_active = True
                    break
        
        # Get unique CMU IDs
        cmu_ids = list(set(components.values_list('cmu_id', flat=True)))
        cmu_ids = [c for c in cmu_ids if c]
        cmu_ids.sort()
        
        # Calculate capacity
        total_capacity = components.aggregate(Sum('derated_capacity_mw'))['derated_capacity_mw__sum'] or 0.0
        
        # Get representative component
        rep_component = components.exclude(
            Q(latitude__isnull=True) | Q(longitude__isnull=True)
        ).first() or components.first()
        
        try:
            # Create LocationGroup with get_or_create to handle any remaining race conditions
            LocationGroup.objects.create(
                location=location,
                component_count=component_count,
                descriptions=descriptions,
                technologies=technologies,
                companies=companies,
                auction_years=auction_years[:10],  # Limit to 10 years
                cmu_ids=cmu_ids,
                displayed_capacity_mw=total_capacity,
                normalized_capacity_mw=total_capacity,
                capacity_confidence='low' if total_capacity == 0 else 'medium',
                capacity_source='derated_capacity_mw',
                is_active=is_active,
                representative_component=rep_component,
                latitude=rep_component.latitude if rep_component else None,
                longitude=rep_component.longitude if rep_component else None,
                county=rep_component.county if rep_component else None,
                outward_code=rep_component.outward_code if rep_component else None,
            )
            return True
        except Exception as e:
            # If we still hit a duplicate key error, just skip this location
            if 'duplicate key' in str(e):
                return False
            raise