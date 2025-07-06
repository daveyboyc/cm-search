from django.core.management.base import BaseCommand
import requests
import time
from django.conf import settings
from checker.models import Component

class Command(BaseCommand):
    help = 'Geocode component locations using Google Maps API with UK-specific handling'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500, 
                          help='Maximum number of components to process (default: 500)')
        parser.add_argument('--force', action='store_true', 
                          help='Re-geocode already processed locations')
        parser.add_argument('--batch', type=int, default=50, 
                          help='Batch size for status updates (default: 50)')
        parser.add_argument(
            '--exclude-companies',
            nargs='+',
            metavar='COMPANY_NAME',
            help='List of company names to exclude from geocoding (case-insensitive)'
        )
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be geocoded without making API calls')

    def is_uk_coordinates(self, lat, lng):
        """Check if coordinates are within UK bounds"""
        # UK roughly bounded by:
        # North: 61°N (Shetland)
        # South: 49°N (Lizard Point)
        # West: 8°W (Western Isles)
        # East: 2°E (Norfolk)
        return 49 <= lat <= 61 and -8 <= lng <= 2

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        batch_size = options['batch']
        excluded_companies = options['exclude_companies']
        dry_run = options['dry_run']
        
        # Get API key from settings
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not api_key and not dry_run:
            self.stderr.write('ERROR: GOOGLE_MAPS_API_KEY not found in settings')
            return
        
        # Build query for components to geocode
        query = Component.objects.all()
        if not force:
            query = query.filter(geocoded=False)
        
        # Apply company exclusion filter if provided
        if excluded_companies:
            for company_name in excluded_companies:
                query = query.exclude(company_name__iexact=company_name)
            self.stdout.write(self.style.NOTICE(f"Excluding companies: {', '.join(excluded_companies)}"))
            
        if limit > 0:
            query = query[:limit]
            
        total = query.count()
        self.stdout.write(f'Found {total} components to geocode')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No API calls will be made'))
        
        processed = 0
        success = 0
        errors = 0
        non_uk_results = 0
        
        for idx, component in enumerate(query, 1):
            if not component.location:
                self.stdout.write(f'Skipping component {component.id}: No location data')
                component.geocoded = True
                if not dry_run:
                    component.save(update_fields=['geocoded'])
                processed += 1
                continue

            # Add ", UK" to the address to bias results
            address_string = f"{component.location}, United Kingdom"
            
            if dry_run:
                self.stdout.write(f"Would geocode: '{address_string}'")
                continue

            try:
                self.stdout.write(self.style.NOTICE(f"  -> Geocoding address: '{address_string}'"))

                # Call Google Geocoding API
                response = requests.get(
                    'https://maps.googleapis.com/maps/api/geocode/json',
                    params={
                        'address': address_string,
                        'key': api_key,
                        'region': 'uk',  # Bias results to UK
                        'components': 'country:GB'  # Restrict to Great Britain
                    }
                )
                
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    result = data['results'][0]
                    location = result['geometry']['location']
                    lat = location['lat']
                    lng = location['lng']
                    
                    # Verify the result is in UK
                    if not self.is_uk_coordinates(lat, lng):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Non-UK result for {component.location}: '
                                f'{lat}, {lng} - {result.get("formatted_address", "Unknown")}'
                            )
                        )
                        non_uk_results += 1
                        errors += 1
                        continue
                    
                    # Check if any address component indicates a non-UK location
                    address_components = result.get('address_components', [])
                    country_code = None
                    for comp in address_components:
                        if 'country' in comp.get('types', []):
                            country_code = comp.get('short_name')
                            break
                    
                    if country_code and country_code not in ['GB', 'UK']:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Non-UK country code {country_code} for {component.location}'
                            )
                        )
                        non_uk_results += 1
                        errors += 1
                        continue
                    
                    # Save the UK coordinates
                    component.latitude = lat
                    component.longitude = lng
                    component.geocoded = True
                    component.save()
                    success += 1
                    
                    if idx % batch_size == 0:
                        self.stdout.write(f'Progress: {idx}/{total} components processed')
                else:
                    self.stdout.write(
                        f'Error geocoding {component.location}: {data.get("status", "Unknown error")}'
                    )
                    errors += 1
                
                # Sleep to avoid hitting API rate limits
                time.sleep(0.2)
                
            except Exception as e:
                self.stderr.write(f'Exception geocoding {component.location}: {str(e)}')
                errors += 1
            
            processed += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nGeocoding complete:'))
        self.stdout.write(f'  Total processed: {processed}')
        self.stdout.write(f'  Successful: {success}')
        self.stdout.write(f'  Errors: {errors}')
        if non_uk_results > 0:
            self.stdout.write(
                self.style.WARNING(f'  Non-UK results rejected: {non_uk_results}')
            )