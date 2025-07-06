"""
Management command to fix Unknown/empty technologies and enhance DSR with specific tech types
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from checker.models import LocationGroup
from collections import defaultdict
import re


class Command(BaseCommand):
    help = 'Fix empty technologies and add specific tech types to DSR records based on descriptions'
    
    # Focused technology patterns for maximum impact
    TECHNOLOGY_PATTERNS = {
        'Battery': [
            'battery', 'bess', 'energy storage', 'lithium', 'battery storage',
            'grid storage', 'batteries', 'lithium ion', 'li-ion'
        ],
        'CHP': [
            'chp', 'combined heat and power', 'cogeneration', 'gas fired chp',
            'co-generation', 'heat and power', 'biomass chp'
        ],
        'OCGT': [
            'gas engine', 'diesel generator', 'gas generator', 'reciprocating engine',
            'gas turbine', 'ocgt', 'open cycle gas turbine', 'gas fired engine',
            'diesel engine', 'natural gas engine'
        ],
        'Solar': [
            'solar', 'photovoltaic', 'pv', 'solar farm', 'solar panels',
            'solar park', 'photovoltaics'
        ],
        'Wind': [
            'wind', 'wind turbine', 'wind farm', 'onshore wind', 'offshore wind',
            'wind power'
        ],
        'Biomass': [
            'biomass', 'landfill gas', 'biogas', 'anaerobic digestion',
            'energy from waste', 'waste to energy', 'sewage gas', 'wood chip'
        ]
    }
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be changed without applying')
        parser.add_argument('--technology', choices=['battery', 'chp', 'ocgt', 'solar', 'wind', 'biomass', 'all'],
                          default='all', help='Which technology to detect')
        parser.add_argument('--target', choices=['empty', 'dsr', 'all'], default='all',
                          help='Target empty technologies, DSR, or both')
        parser.add_argument('--limit', type=int, default=None,
                          help='Limit number of records to process')
        parser.add_argument('--exclude-companies', nargs='+', default=['Octopus', 'Axle'],
                          help='Company names to exclude from DSR processing')
    
    def handle(self, *args, **options):
        # Build target queryset
        target_conditions = Q()
        
        if options['target'] in ['empty', 'all']:
            target_conditions |= Q(technologies={})  # Empty technologies (grey markers)
            
        if options['target'] in ['dsr', 'all']:
            dsr_condition = Q(technologies__has_key='DSR')  # DSR records
            
            # If focusing on battery technology for DSR, only include DSR records with battery terms
            if options['technology'] == 'battery':
                battery_terms_condition = Q()
                for term in self.TECHNOLOGY_PATTERNS['Battery']:
                    battery_terms_condition |= Q(descriptions__icontains=term)
                dsr_condition = dsr_condition & battery_terms_condition
                
            target_conditions |= dsr_condition
            
        target_qs = (LocationGroup.objects
                    .filter(target_conditions)
                    .exclude(descriptions=[])  # Must have descriptions
                    .order_by('id'))
        
        # Apply company exclusions for DSR processing
        if options['target'] in ['dsr', 'all'] and options['exclude_companies']:
            exclude_conditions = Q()
            for company in options['exclude_companies']:
                # Check all descriptions for company name matches
                exclude_conditions |= Q(descriptions__icontains=company)
            
            # Only exclude from DSR records, not empty ones
            dsr_exclusions = (LocationGroup.objects
                            .filter(Q(technologies__has_key='DSR') & exclude_conditions)
                            .values_list('id', flat=True))
            
            target_qs = target_qs.exclude(id__in=dsr_exclusions)
            
            self.stdout.write(f"🚫 Excluding {len(dsr_exclusions)} DSR records from companies: {', '.join(options['exclude_companies'])}")
        
        if options['limit']:
            target_qs = target_qs[:options['limit']]
            
        # Filter technology patterns if specific tech requested
        tech_patterns = self.TECHNOLOGY_PATTERNS
        if options['technology'] != 'all':
            tech_key = options['technology'].title()
            if tech_key in tech_patterns:
                tech_patterns = {tech_key: tech_patterns[tech_key]}
        
        # Results tracking
        results = {
            'processed': 0,
            'updated': 0,
            'by_technology': defaultdict(int),
            'empty_fixed': 0,
            'dsr_enhanced': 0
        }
        
        self.stdout.write(f"🔍 Processing {target_qs.count()} LocationGroups...")
        
        for location_group in target_qs:
            detection_result = self.detect_technology(location_group, tech_patterns)
            
            if detection_result:
                original_techs = list(location_group.technologies.keys()) or ['Empty']
                
                if not options['dry_run']:
                    self.update_location_group(location_group, detection_result)
                    results['updated'] += 1
                    
                    # Track type of update
                    if not location_group.technologies:  # Was empty
                        results['empty_fixed'] += 1
                    elif 'DSR' in location_group.technologies:
                        results['dsr_enhanced'] += 1
                
                results['by_technology'][detection_result['technology']] += 1
                
                # Show the change
                self.stdout.write(f"📍 {location_group.location}")
                self.stdout.write(f"   Original: {original_techs}")
                self.stdout.write(f"   Adding:   {detection_result['technology']}")
                self.stdout.write(f"   Evidence: {', '.join(detection_result['matched_terms'][:3])}")
                self.stdout.write(f"   Description: {detection_result['description'][:80]}...")
                self.stdout.write("")
                
            results['processed'] += 1
        
        # Summary
        self.stdout.write("="*60)
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   Processed: {results['processed']} records")
        self.stdout.write(f"   Updated:   {results['updated']} records")
        self.stdout.write(f"   Empty technologies fixed: {results['empty_fixed']}")
        self.stdout.write(f"   DSR records enhanced: {results['dsr_enhanced']}")
        self.stdout.write("")
        
        if results['by_technology']:
            self.stdout.write("🏷️  Technologies detected:")
            for tech, count in sorted(results['by_technology'].items()):
                self.stdout.write(f"   {tech}: {count} locations")
        
        if options['dry_run']:
            self.stdout.write("")
            self.stdout.write("🚫 DRY RUN - No changes applied. Run without --dry-run to apply changes.")
    
    def detect_technology(self, location_group, tech_patterns):
        """
        Analyze descriptions and return best technology match
        """
        # Combine all descriptions into one searchable text
        all_descriptions = ' '.join(location_group.descriptions).lower()
        
        # Try each technology pattern
        for tech, patterns in tech_patterns.items():
            matches = [term for term in patterns if term in all_descriptions]
            if matches:
                # Calculate confidence based on match quality
                confidence = self.calculate_confidence(matches, patterns, all_descriptions)
                
                return {
                    'technology': tech,
                    'confidence': confidence,
                    'matched_terms': matches,
                    'description': location_group.descriptions[0]  # First description for context
                }
        
        return None
    
    def calculate_confidence(self, matches, all_patterns, text):
        """
        Calculate confidence score (0.0 to 1.0) based on match quality
        """
        # Basic confidence from match ratio
        match_ratio = len(matches) / len(all_patterns)
        
        # Bonus for longer/more specific terms
        avg_term_length = sum(len(term.split()) for term in matches) / len(matches)
        specificity_bonus = min(0.4, avg_term_length * 0.1)
        
        # Bonus for multiple matches
        multiple_match_bonus = min(0.2, (len(matches) - 1) * 0.1)
        
        confidence = match_ratio * 0.4 + specificity_bonus + multiple_match_bonus
        return min(1.0, confidence)
    
    def update_location_group(self, location_group, detection_result):
        """
        Update the LocationGroup with detected technology (additive approach)
        """
        # Get current technologies (copy to avoid mutation)
        technologies = location_group.technologies.copy() if location_group.technologies else {}
        
        # Add the detected technology (keeping existing DSR if present)
        component_count = location_group.component_count or 1
        technologies[detection_result['technology']] = component_count
        
        # Save the updated technologies
        location_group.technologies = technologies
        location_group.save(update_fields=['technologies'])
        
        # Log the change for audit
        self.log_technology_change(location_group, detection_result)
    
    def log_technology_change(self, location_group, detection_result):
        """
        Log the technology change for audit purposes
        """
        self.stdout.write(
            f"✅ Updated {location_group.id}: Added {detection_result['technology']} "
            f"(confidence: {detection_result['confidence']:.2f})",
            self.style.SUCCESS
        )