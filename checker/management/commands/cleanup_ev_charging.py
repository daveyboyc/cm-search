"""
Management command to remove EV Charging technology from records that only have 
'domestic demand turn down' descriptions (which should be DSR only)
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from checker.models import LocationGroup
from collections import defaultdict


class Command(BaseCommand):
    help = 'Remove EV Charging technology from locations that only have "domestic demand turn down" descriptions'
    
    # Valid EV charging patterns (excluding the incorrect "domestic demand turn down")
    VALID_EV_PATTERNS = [
        'domestic ev charger',
        'ev charging',
        'electric vehicle charging',
        'ev charging at residential premises',
        'residential ev',
        'domestic ev'
    ]
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be changed without applying')
    
    def handle(self, *args, **options):
        # Find all locations that have EV Charging technology
        target_qs = (LocationGroup.objects
                    .filter(technologies__has_key='EV Charging')
                    .exclude(descriptions=[])
                    .order_by('id'))
        
        # Results tracking
        results = {
            'processed': 0,
            'updated': 0,
            'kept_ev_charging': 0,
            'by_pattern': defaultdict(int),
            'by_company': defaultdict(int)
        }
        
        total_count = target_qs.count()
        self.stdout.write(f"🔍 Processing {total_count} LocationGroups with EV Charging technology...")
        
        for location_group in target_qs:
            all_descriptions = ' '.join(location_group.descriptions).lower()
            
            # Check if it has valid EV charging patterns
            has_valid_ev_patterns = any(pattern.lower() in all_descriptions 
                                      for pattern in self.VALID_EV_PATTERNS)
            
            # Check if it ONLY has "domestic demand turn down" (and no other EV patterns)
            has_demand_turn_down = 'domestic demand turn down' in all_descriptions
            
            # Extract company name
            company_name = self.extract_company_name(location_group.descriptions)
            
            if has_demand_turn_down and not has_valid_ev_patterns:
                # This should NOT have EV Charging technology - remove it
                if not options['dry_run']:
                    technologies = location_group.technologies.copy()
                    if 'EV Charging' in technologies:
                        del technologies['EV Charging']
                        location_group.technologies = technologies
                        location_group.save(update_fields=['technologies'])
                        results['updated'] += 1
                
                # Show the change
                self.stdout.write(f"❌ REMOVING EV Charging from: {location_group.location[:50]}")
                self.stdout.write(f"   Company: {company_name}")
                self.stdout.write(f"   Description: {location_group.descriptions[0][:80]}...")
                self.stdout.write(f"   Reason: Only has 'domestic demand turn down', no valid EV patterns")
                self.stdout.write("")
                
                results['by_pattern']['domestic demand turn down only'] += 1
            else:
                # This correctly has EV Charging technology - keep it
                results['kept_ev_charging'] += 1
                if has_valid_ev_patterns:
                    valid_patterns = [pattern for pattern in self.VALID_EV_PATTERNS 
                                    if pattern.lower() in all_descriptions]
                    for pattern in valid_patterns:
                        results['by_pattern'][f'valid: {pattern}'] += 1
            
            results['by_company'][company_name] += 1
            results['processed'] += 1
        
        # Summary
        self.stdout.write("="*60)
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   Processed: {results['processed']} records")
        self.stdout.write(f"   Updated (removed EV Charging): {results['updated']} records")
        self.stdout.write(f"   Kept EV Charging: {results['kept_ev_charging']} records")
        self.stdout.write("")
        
        if results['by_company']:
            self.stdout.write("🏢 By company:")
            for company, count in sorted(results['by_company'].items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"   {company}: {count} locations")
            self.stdout.write("")
        
        if results['by_pattern']:
            self.stdout.write("🏷️  Patterns found:")
            for pattern, count in sorted(results['by_pattern'].items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"   '{pattern}': {count} locations")
        
        if options['dry_run']:
            self.stdout.write("")
            self.stdout.write("🚫 DRY RUN - No changes applied. Run without --dry-run to apply changes.")
    
    def extract_company_name(self, descriptions):
        """Extract company name from descriptions"""
        all_text = ' '.join(descriptions).lower()
        
        if 'axle energy' in all_text:
            return 'Axle Energy Limited'
        elif 'octopus' in all_text:
            return 'Octopus Energy'
        elif any(term in all_text for term in ['domestic', 'residential']):
            return 'Domestic/Residential'
        else:
            first_desc = descriptions[0] if descriptions else ''
            if len(first_desc) > 0:
                return first_desc[:30].strip()
            return 'Unknown'