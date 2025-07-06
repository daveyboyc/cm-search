"""
Management command to add EV Charging technology to records with EV charging descriptions
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from checker.models import LocationGroup
from collections import defaultdict


class Command(BaseCommand):
    help = 'Add EV Charging technology to locations with EV charging descriptions'
    
    # EV charging patterns to identify
    EV_PATTERNS = [
        'domestic ev charger',
        'ev charging',
        'electric vehicle charging',
        'ev charging at residential premises',
        'residential ev',
        'domestic ev',
        'bus depot',
        'bus depots',
        'electric vehicle'
    ]
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be changed without applying')
        parser.add_argument('--company', type=str, default='Axle Energy Limited',
                          help='Target specific company (default: Axle Energy Limited)')
        parser.add_argument('--limit', type=int, default=None,
                          help='Limit number of records to process')
        parser.add_argument('--all-companies', action='store_true',
                          help='Apply to all companies with EV patterns, not just specified company')
    
    def handle(self, *args, **options):
        # Find all locations with EV charging patterns in descriptions
        ev_conditions = Q()
        for pattern in self.EV_PATTERNS:
            ev_conditions |= Q(descriptions__icontains=pattern)
        
        target_qs = (LocationGroup.objects
                    .filter(ev_conditions)
                    .exclude(descriptions=[])
                    .order_by('id'))
        
        # Filter by company if specified
        if not options['all_companies'] and options['company']:
            # We'll filter by description patterns since company field structure is unclear
            company_filter = Q(descriptions__icontains=options['company'])
            target_qs = target_qs.filter(company_filter)
            self.stdout.write(f"🎯 Targeting company: {options['company']}")
        elif options['all_companies']:
            self.stdout.write(f"🌐 Targeting all companies with EV patterns")
        
        if options['limit']:
            target_qs = target_qs[:options['limit']]
        
        # Results tracking
        results = {
            'processed': 0,
            'updated': 0,
            'already_had_ev_charging': 0,
            'by_pattern': defaultdict(int),
            'by_company': defaultdict(int)
        }
        
        total_count = target_qs.count()
        self.stdout.write(f"🔍 Processing {total_count} LocationGroups with EV charging patterns...")
        
        for location_group in target_qs:
            # Check if already has EV Charging technology
            has_ev_charging = 'EV Charging' in location_group.technologies
            
            # Find which EV patterns match
            all_descriptions = ' '.join(location_group.descriptions).lower()
            matched_patterns = [pattern for pattern in self.EV_PATTERNS 
                              if pattern.lower() in all_descriptions]
            
            # Identify company from descriptions
            company_name = self.extract_company_name(location_group.descriptions)
            
            if not has_ev_charging and matched_patterns:
                if not options['dry_run']:
                    # Add EV Charging technology
                    technologies = location_group.technologies.copy()
                    component_count = location_group.component_count or 1
                    technologies['EV Charging'] = component_count
                    
                    location_group.technologies = technologies
                    location_group.save(update_fields=['technologies'])
                    results['updated'] += 1
                
                # Track by pattern and company
                for pattern in matched_patterns:
                    results['by_pattern'][pattern] += 1
                results['by_company'][company_name] += 1
                
                # Show the change
                self.stdout.write(f"📍 {location_group.location[:50]}")
                self.stdout.write(f"   Company: {company_name}")
                self.stdout.write(f"   Original techs: {list(location_group.technologies.keys())}")
                self.stdout.write(f"   Adding: EV Charging")
                self.stdout.write(f"   Matched patterns: {matched_patterns[:2]}")  # Show first 2 patterns
                self.stdout.write(f"   Description: {location_group.descriptions[0][:80]}...")
                self.stdout.write("")
                
            elif has_ev_charging:
                results['already_had_ev_charging'] += 1
                results['by_company'][company_name] += 1
                
            results['processed'] += 1
        
        # Summary
        self.stdout.write("="*60)
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   Processed: {results['processed']} records")
        self.stdout.write(f"   Updated:   {results['updated']} records")
        self.stdout.write(f"   Already had EV Charging: {results['already_had_ev_charging']} records")
        self.stdout.write("")
        
        if results['by_company']:
            self.stdout.write("🏢 By company:")
            for company, count in sorted(results['by_company'].items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"   {company}: {count} locations")
            self.stdout.write("")
        
        if results['by_pattern']:
            self.stdout.write("🏷️  Patterns matched:")
            for pattern, count in sorted(results['by_pattern'].items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"   '{pattern}': {count} locations")
        
        if options['dry_run']:
            self.stdout.write("")
            self.stdout.write("🚫 DRY RUN - No changes applied. Run without --dry-run to apply changes.")
    
    def extract_company_name(self, descriptions):
        """Extract company name from descriptions"""
        # Look for common company indicators in descriptions
        all_text = ' '.join(descriptions).lower()
        
        if 'axle energy' in all_text:
            return 'Axle Energy Limited'
        elif 'octopus' in all_text:
            return 'Octopus Energy'
        elif any(term in all_text for term in ['domestic', 'residential']):
            return 'Domestic/Residential'
        else:
            # Try to extract from first part of description
            first_desc = descriptions[0] if descriptions else ''
            if len(first_desc) > 0:
                # Return first 30 chars as potential company identifier
                return first_desc[:30].strip()
            return 'Unknown'