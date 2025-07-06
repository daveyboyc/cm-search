"""
Management command to add Battery technology to all storage-related technologies
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from checker.models import LocationGroup
from collections import defaultdict


class Command(BaseCommand):
    help = 'Add Battery technology to all locations with storage-related technologies'
    
    # Storage technology patterns to identify - all variations found in the database
    STORAGE_PATTERNS = [
        'Storage',
        'Storage (Duration 0.5h)',
        'Storage (Duration 1.5h)', 
        'Storage (Duration 12h)',
        'Storage (Duration 1h)',
        'Storage (Duration 2.5h)',
        'Storage (Duration 2h)',
        'Storage (Duration 3.5h)',
        'Storage (Duration 3h)',
        'Storage (Duration 4.5h)',
        'Storage (Duration 4h)',
        'Storage (Duration 5.5h)',
        'Storage (Duration 5h)',
        'Storage (Duration 6h)',
        'Storage (Duration 7h)',
        'Storage (Duration 8h)',
        'Storage (Duration 9.5h)',
        'Storage (Duration 9h)',
        'Battery'  # Include Battery to catch any existing ones without proper grouping
    ]
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be changed without applying')
        parser.add_argument('--limit', type=int, default=None,
                          help='Limit number of records to process')
    
    def handle(self, *args, **options):
        # Find all locations with storage-related technologies
        storage_conditions = Q()
        for pattern in self.STORAGE_PATTERNS:
            # Exact match for all patterns
            storage_conditions |= Q(technologies__has_key=pattern)
        
        target_qs = LocationGroup.objects.filter(storage_conditions).order_by('id')
        
        if options['limit']:
            target_qs = target_qs[:options['limit']]
        
        # Results tracking
        results = {
            'processed': 0,
            'updated': 0,
            'already_had_battery': 0,
            'by_storage_type': defaultdict(int)
        }
        
        self.stdout.write(f"🔍 Processing {target_qs.count()} LocationGroups with storage technologies...")
        
        for location_group in target_qs:
            # Check if already has Battery technology
            has_battery = 'Battery' in location_group.technologies
            
            # Find storage technologies in this location
            storage_techs = [tech for tech in location_group.technologies.keys() 
                           if any(pattern.lower() in tech.lower() for pattern in self.STORAGE_PATTERNS)]
            
            if not has_battery and storage_techs:
                if not options['dry_run']:
                    # Add Battery technology with same count as first storage tech
                    technologies = location_group.technologies.copy()
                    component_count = location_group.component_count or 1
                    technologies['Battery'] = component_count
                    
                    location_group.technologies = technologies
                    location_group.save(update_fields=['technologies'])
                    results['updated'] += 1
                
                # Track by storage type
                for tech in storage_techs:
                    results['by_storage_type'][tech] += 1
                
                # Show the change
                self.stdout.write(f"📍 {location_group.location[:60]}")
                self.stdout.write(f"   Storage techs: {storage_techs}")
                self.stdout.write(f"   Adding: Battery")
                self.stdout.write("")
                
            elif has_battery:
                results['already_had_battery'] += 1
                
            results['processed'] += 1
        
        # Summary
        self.stdout.write("="*60)
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   Processed: {results['processed']} records")
        self.stdout.write(f"   Updated:   {results['updated']} records")
        self.stdout.write(f"   Already had Battery: {results['already_had_battery']} records")
        self.stdout.write("")
        
        if results['by_storage_type']:
            self.stdout.write("🏷️  Storage technologies processed:")
            for tech, count in sorted(results['by_storage_type'].items()):
                self.stdout.write(f"   {tech}: {count} locations")
        
        if options['dry_run']:
            self.stdout.write("")
            self.stdout.write("🚫 DRY RUN - No changes applied. Run without --dry-run to apply changes.")