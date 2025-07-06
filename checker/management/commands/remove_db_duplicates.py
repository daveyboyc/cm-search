from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from django.db import transaction
from checker.models import Component
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Detect and remove duplicate component records from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be removed without making changes'
        )
        parser.add_argument(
            '--match-level',
            type=str,
            default='standard',
            choices=['exact', 'standard', 'relaxed'],
            help='How strict to be when matching duplicates'
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Only check duplicates for a specific company'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        match_level = options['match_level']
        company_filter = options['company']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Define fields for duplicate detection based on match level
        if match_level == 'exact':
            # All important fields must match
            duplicate_fields = [
                'cmu_id', 'location', 'description', 'technology',
                'company_name', 'delivery_year', 'auction_name',
                'derated_capacity_mw', 'longitude', 'latitude'
            ]
        elif match_level == 'standard':
            # Core identifying fields
            duplicate_fields = [
                'cmu_id', 'location', 'description', 'technology',
                'company_name', 'delivery_year', 'auction_name'
            ]
        else:  # relaxed
            # Minimal fields - might catch more false positives
            duplicate_fields = [
                'cmu_id', 'location', 'company_name', 'delivery_year'
            ]

        self.stdout.write(f"Using {match_level} matching with fields: {', '.join(duplicate_fields)}")

        # Build the base queryset
        components = Component.objects.all()
        
        if company_filter:
            components = components.filter(company_name__icontains=company_filter)
            self.stdout.write(f"Filtering by company: {company_filter}")

        # Find duplicate groups
        self.stdout.write("Analyzing database for duplicates...")
        
        # Group by the duplicate fields and count
        duplicate_groups = (
            components
            .values(*duplicate_fields)
            .annotate(
                count=Count('id'),
                min_id=Min('id')  # Keep the oldest record (lowest ID)
            )
            .filter(count__gt=1)
            .order_by('-count')
        )

        total_duplicates = 0
        duplicate_sets = 0

        self.stdout.write(f"Found {duplicate_groups.count()} duplicate groups")

        if not duplicate_groups.exists():
            self.stdout.write(self.style.SUCCESS("No duplicates found!"))
            return

        # Process each duplicate group
        for group in duplicate_groups:
            duplicate_sets += 1
            group_count = group['count']
            duplicates_in_group = group_count - 1  # Subtract 1 because we keep one
            total_duplicates += duplicates_in_group

            # Get the actual component records in this group
            filter_kwargs = {field: group[field] for field in duplicate_fields}
            group_components = components.filter(**filter_kwargs).order_by('id')

            self.stdout.write(f"\nDuplicate Group #{duplicate_sets} ({group_count} identical components):")
            
            # Show details of the first component (the one we'll keep)
            first_component = group_components.first()
            self.stdout.write(f"  Will KEEP: ID {first_component.id}")
            self.stdout.write(f"    Company: {first_component.company_name}")
            self.stdout.write(f"    Location: {first_component.location}")
            self.stdout.write(f"    CMU ID: {first_component.cmu_id}")
            self.stdout.write(f"    Technology: {first_component.technology}")
            self.stdout.write(f"    Year: {first_component.delivery_year}")
            self.stdout.write(f"    Auction: {first_component.auction_name}")

            # Show the duplicates we'll remove
            duplicates_to_remove = group_components[1:]  # Skip the first one
            for dup in duplicates_to_remove:
                self.stdout.write(f"  Will REMOVE: ID {dup.id}")

            if not dry_run:
                # Remove the duplicates (keep the first/oldest one)
                with transaction.atomic():
                    deleted_count = 0
                    for dup in duplicates_to_remove:
                        dup.delete()
                        deleted_count += 1
                    self.stdout.write(f"    ✓ Removed {deleted_count} duplicate(s)")

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"SUMMARY:")
        self.stdout.write(f"  Duplicate groups found: {duplicate_sets}")
        self.stdout.write(f"  Total duplicate records: {total_duplicates}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"  Would remove: {total_duplicates} records"))
            self.stdout.write(self.style.WARNING("  Run without --dry-run to actually remove duplicates"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  Removed: {total_duplicates} duplicate records"))
            self.stdout.write(self.style.SUCCESS("  Database cleanup complete!"))

        # Show example of checking specific company
        if not company_filter:
            self.stdout.write("\nTo check a specific company, use:")
            self.stdout.write("  python manage.py remove_db_duplicates --company 'Vital Energi' --dry-run")