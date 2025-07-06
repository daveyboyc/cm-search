import os
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Toggle maintenance mode on/off'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable', 
            action='store_true',
            help='Enable maintenance mode'
        )
        parser.add_argument(
            '--disable', 
            action='store_true', 
            help='Disable maintenance mode'
        )
        parser.add_argument(
            '--status', 
            action='store_true',
            help='Show current maintenance mode status'
        )

    def handle(self, *args, **options):
        if options['status']:
            current_status = getattr(settings, 'MAINTENANCE_MODE', False)
            env_status = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
            self.stdout.write(f"Settings MAINTENANCE_MODE: {current_status}")
            self.stdout.write(f"Environment MAINTENANCE_MODE: {env_status}")
            return
            
        if options['enable']:
            os.environ['MAINTENANCE_MODE'] = 'true'
            self.stdout.write(
                self.style.WARNING('Maintenance mode ENABLED')
            )
            self.stdout.write('Set environment variable: export MAINTENANCE_MODE=true')
            self.stdout.write('The site will show maintenance page for all users except allowed IPs')
            
        elif options['disable']:
            os.environ['MAINTENANCE_MODE'] = 'false'
            self.stdout.write(
                self.style.SUCCESS('Maintenance mode DISABLED')
            )
            self.stdout.write('Set environment variable: export MAINTENANCE_MODE=false')
            self.stdout.write('The site will function normally')
            
        else:
            self.stdout.write('Use --enable, --disable, or --status')
            
        # Show how to test
        self.stdout.write('\n--- Testing Instructions ---')
        self.stdout.write('1. View maintenance page: http://localhost:8000/maintenance/')
        self.stdout.write('2. Test full site maintenance: Set MAINTENANCE_MODE=true and visit any page')
        self.stdout.write('3. Bypass maintenance: Add your IP to MAINTENANCE_ALLOWED_IPS in settings.py')