"""
Management command to fix missed ASDA locations in Flexitricity "load curtailment from refrigeration" entries.
Re-runs enhanced ASDA-specific search on locations that weren't properly identified.
"""
import time
import requests
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from checker.models import LocationGroup, Component
from django.db.models import Q


class Command(BaseCommand):
    help = 'Fix missed ASDA locations in Flexitricity refrigeration entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of locations to process'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay between API requests in seconds'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.delay = options['delay']
        
        # Check API key
        if not hasattr(settings, 'GOOGLE_MAPS_API_KEY') or not settings.GOOGLE_MAPS_API_KEY:
            self.stdout.write(
                self.style.ERROR('GOOGLE_MAPS_API_KEY not configured in settings')
            )
            return

        self.stdout.write("=== FIXING MISSED ASDA LOCATIONS IN REFRIGERATION ENTRIES ===")
        
        # Find Flexitricity locations with 'load curtailment from refrigeration' that don't have ASDA
        missed_asda = LocationGroup.objects.filter(
            companies__icontains='flexitricity',
            descriptions__icontains='load curtailment from refridgeration'  # Note: using same misspelling as in data
        ).exclude(
            Q(location__icontains='asda') | 
            Q(representative_component__places_api_business_name__icontains='asda') |
            Q(representative_component__places_api_major_retailers__contains=['ASDA'])
        ).filter(
            representative_component__full_postcode__isnull=False
        ).select_related('representative_component')
        
        if options['limit']:
            missed_asda = missed_asda[:options['limit']]
        
        total_count = missed_asda.count()
        self.stdout.write(f"Found {total_count} Flexitricity refrigeration locations to re-search for ASDA stores")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        asda_found_count = 0
        processed_count = 0
        
        for lg in missed_asda:
            processed_count += 1
            rep = lg.representative_component
            
            self.stdout.write(f"\n--- Processing {processed_count}/{total_count}: LocationGroup {lg.id} ---")
            self.stdout.write(f"Location: {lg.location}")
            self.stdout.write(f"Postcode: {rep.full_postcode}")
            self.stdout.write(f"Current business: {rep.places_api_business_name}")
            
            if self.dry_run:
                self.stdout.write("DRY RUN: Would call ASDA-specific Places API search")
                continue
            
            # Run ASDA-specific enhanced search
            asda_result = self.search_for_asda_specifically(lg.location, rep.full_postcode)
            
            if asda_result:
                self.stdout.write(f"🎯 ASDA FOUND: {asda_result['name']}")
                
                # Update representative component
                old_business = rep.places_api_business_name
                rep.places_api_business_name = asda_result['name']
                rep.places_api_confidence = asda_result['confidence']
                rep.places_api_search_strategy = 'asda_specific_fix'
                rep.places_api_major_retailers = ['ASDA']
                rep.places_api_business_type = 'supermarket'
                rep.places_api_last_checked = timezone.now()
                rep.save()
                
                # Rename the LocationGroup
                old_location = lg.location
                asda_clean = self.clean_asda_name(asda_result['name'])
                new_location = f"{asda_clean}, {old_location}"
                
                # Ensure it's not too long
                if len(new_location) > 255:
                    new_location = new_location[:252] + "..."
                
                lg.location = new_location
                lg.save()
                
                # Update all components at this location
                updated_components = Component.objects.filter(location=old_location).update(location=new_location)
                
                self.stdout.write(f"✅ UPDATED:")
                self.stdout.write(f"   Business: '{old_business}' → '{asda_result['name']}'")
                self.stdout.write(f"   Location: '{old_location}' → '{new_location}'")
                self.stdout.write(f"   Updated {updated_components} components")
                
                asda_found_count += 1
            else:
                self.stdout.write("❌ No ASDA store found with enhanced search")
                
                # Still update the last_checked to avoid re-processing
                rep.places_api_last_checked = timezone.now()
                rep.save()
            
            # Rate limiting
            time.sleep(self.delay)
        
        if not self.dry_run:
            self.stdout.write(f"\n🎯 COMPLETE: Found and fixed {asda_found_count} additional ASDA stores out of {processed_count} locations processed")
        else:
            self.stdout.write(f"\nDRY RUN COMPLETE: Would process {total_count} locations")

    def search_for_asda_specifically(self, location, postcode):
        """Enhanced ASDA-specific search with multiple strategies"""
        
        # ASDA-focused search strategies
        search_strategies = [
            f"ASDA {location} {postcode} UK",
            f"ASDA {postcode} UK",
            f"ASDA supermarket {postcode}",
            f"ASDA store {postcode}",
            f"ASDA superstore {postcode}",
            f"supermarket {location} {postcode}"
        ]
        
        self.stdout.write(f"   Enhanced ASDA search for: {location}, {postcode}")
        
        for strategy_query in search_strategies:
            self.stdout.write(f"   → Trying: {strategy_query}")
            
            results = self.call_places_api_raw(strategy_query)
            if results:
                self.stdout.write(f"     Found {len(results)} result(s)")
                
                # Check first few results for ASDA
                for result in results[:3]:
                    business_name = result.get('name', '')
                    if 'asda' in business_name.lower():
                        self.stdout.write(f"     🎯 ASDA FOUND: {business_name}")
                        return {
                            'name': business_name,
                            'confidence': 0.95,
                            'strategy': 'asda_specific_fix',
                            'types': result.get('types', [])
                        }
                
                self.stdout.write(f"     No ASDA in results")
            else:
                self.stdout.write(f"     No results")
            
            # Small delay between strategies
            time.sleep(0.2)
        
        return None

    def call_places_api_raw(self, query):
        """Make raw Places API call and return all results"""
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        # Clean up query
        search_query = re.sub(r'\\s+', ' ', query.strip())
        
        params = {
            'query': search_query,
            'key': settings.GOOGLE_MAPS_API_KEY,
            'fields': 'name,business_status,rating,types,place_id'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                results = data.get('results', [])
                return results
            
            return []
            
        except Exception:
            return []

    def clean_asda_name(self, asda_name):
        """Clean ASDA store name for location display"""
        if not asda_name:
            return "ASDA"
        
        # Remove common suffixes to keep it concise
        name = asda_name.replace("Superstore", "").replace("Supercentre", "").replace("Supermarket", "")
        name = name.replace("Store", "").strip()
        
        # Remove trailing comma if present
        if name.endswith(","):
            name = name[:-1].strip()
        
        return name or "ASDA"