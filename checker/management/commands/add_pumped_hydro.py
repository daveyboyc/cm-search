"""
Management command to add Pumped Hydro technology to pumped storage facilities
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from checker.models import LocationGroup
from collections import defaultdict


class Command(BaseCommand):
    help = 'Add Pumped Hydro technology to locations with pumped storage descriptions'
    
    # Pumped storage patterns to identify
    PUMPED_PATTERNS = [
        'pumped storage',
        'pumped hydro',
        'pumped storage hydro',
        'pumped storage facility'
    ]
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be changed without applying')
        parser.add_argument('--limit', type=int, default=None,
                          help='Limit number of records to process')
    
    def handle(self, *args, **options):
        # Find all locations with pumped storage in descriptions
        pumped_conditions = Q()
        for pattern in self.PUMPED_PATTERNS:
            pumped_conditions |= Q(descriptions__icontains=pattern)
        
        target_qs = (LocationGroup.objects
                    .filter(pumped_conditions)
                    .exclude(descriptions=[])
                    .order_by('id'))
        
        if options['limit']:
            target_qs = target_qs[:options['limit']]
        
        # Results tracking
        results = {
            'processed': 0,
            'updated': 0,
            'already_had_pumped_hydro': 0,
            'by_pattern': defaultdict(int)
        }
        
        self.stdout.write(f"🔍 Processing {target_qs.count()} LocationGroups with pumped storage descriptions...")
        
        for location_group in target_qs:
            # Check if already has Pumped Hydro technology
            has_pumped_hydro = 'Pumped Hydro' in location_group.technologies
            
            # Find which pumped patterns match
            all_descriptions = ' '.join(location_group.descriptions).lower()
            matched_patterns = [pattern for pattern in self.PUMPED_PATTERNS 
                              if pattern.lower() in all_descriptions]
            
            if not has_pumped_hydro and matched_patterns:
                if not options['dry_run']:
                    # Add Pumped Hydro technology
                    technologies = location_group.technologies.copy()
                    component_count = location_group.component_count or 1
                    technologies['Pumped Hydro'] = component_count
                    
                    location_group.technologies = technologies
                    location_group.save(update_fields=['technologies'])
                    results['updated'] += 1
                
                # Track by pattern
                for pattern in matched_patterns:
                    results['by_pattern'][pattern] += 1
                
                # Show the change
                self.stdout.write(f"📍 {location_group.location[:60]}")
                self.stdout.write(f"   Original techs: {list(location_group.technologies.keys())}")
                self.stdout.write(f"   Adding: Pumped Hydro")
                self.stdout.write(f"   Matched patterns: {matched_patterns}")
                self.stdout.write(f"   Description: {location_group.descriptions[0][:100]}...")
                self.stdout.write("")
                
            elif has_pumped_hydro:
                results['already_had_pumped_hydro'] += 1
                
            results['processed'] += 1
        
        # Summary
        self.stdout.write("="*60)
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   Processed: {results['processed']} records")
        self.stdout.write(f"   Updated:   {results['updated']} records")
        self.stdout.write(f"   Already had Pumped Hydro: {results['already_had_pumped_hydro']} records")
        self.stdout.write("")
        
        if results['by_pattern']:
            self.stdout.write("🏷️  Patterns matched:")
            for pattern, count in sorted(results['by_pattern'].items()):
                self.stdout.write(f"   '{pattern}': {count} locations")
        
        if options['dry_run']:
            self.stdout.write("")
            self.stdout.write("🚫 DRY RUN - No changes applied. Run without --dry-run to apply changes.")