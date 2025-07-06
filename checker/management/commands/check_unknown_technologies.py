"""
Management command to check how many LocationGroups have Unknown technologies
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from checker.models import LocationGroup


class Command(BaseCommand):
    help = 'Check how many LocationGroups have Unknown/DSR technologies and show sample descriptions'
    
    def add_arguments(self, parser):
        parser.add_argument('--samples', type=int, default=20, 
                          help='Number of sample descriptions to show')
        parser.add_argument('--technology', choices=['unknown', 'dsr', 'all'], default='all',
                          help='Which technology to analyze')
    
    def handle(self, *args, **options):
        # Count Unknown technologies
        unknown_count = LocationGroup.objects.filter(technologies__has_key='Unknown').count()
        self.stdout.write(f'📊 LocationGroups with Unknown technology: {unknown_count}')
        
        # Count DSR technologies  
        dsr_count = LocationGroup.objects.filter(technologies__has_key='DSR').count()
        self.stdout.write(f'📊 LocationGroups with DSR technology: {dsr_count}')
        
        # Count empty technologies
        empty_count = LocationGroup.objects.filter(technologies={}).count()
        self.stdout.write(f'📊 LocationGroups with empty technologies: {empty_count}')
        
        total_count = LocationGroup.objects.count()
        self.stdout.write(f'📊 Total LocationGroups: {total_count}')
        
        # Show samples based on option
        if options['technology'] in ['unknown', 'all']:
            self.show_samples('Unknown', options['samples'])
            
        if options['technology'] in ['dsr', 'all']:
            self.show_samples('DSR', options['samples'])
    
    def show_samples(self, tech_type, sample_count):
        """Show sample descriptions for a technology type"""
        self.stdout.write(f'\n📋 Sample {tech_type} technology descriptions:')
        
        samples = (LocationGroup.objects
                  .filter(technologies__has_key=tech_type)
                  .exclude(descriptions=[])
                  [:sample_count])
        
        if not samples:
            self.stdout.write(f'   No {tech_type} technologies with descriptions found')
            return
            
        for i, lg in enumerate(samples, 1):
            descriptions = lg.descriptions or ['No description']
            first_desc = descriptions[0][:100] + ('...' if len(descriptions[0]) > 100 else '')
            
            self.stdout.write(f'{i:2d}. {lg.location}')
            self.stdout.write(f'    Description: {first_desc}')
            self.stdout.write(f'    Technologies: {list(lg.technologies.keys())}')
            self.stdout.write('')