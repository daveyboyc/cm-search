"""
Smart business identification command using Places API with decision matrix.
Prevents false positives by using multiple verification strategies.
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
    help = 'Smart business identification with decision matrix to prevent false positives'

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

        self.stdout.write("=== SMART BUSINESS IDENTIFICATION ===")
        
        # Find locations without business information
        unknown_locations = LocationGroup.objects.filter(
            representative_component__places_api_business_name__isnull=True,
            representative_component__full_postcode__isnull=False
        ).exclude(
            # Skip already processed locations
            location__icontains='asda'
        ).select_related('representative_component')
        
        if options['limit']:
            unknown_locations = unknown_locations[:options['limit']]
        
        total_count = unknown_locations.count()
        self.stdout.write(f"Found {total_count} locations without business identification")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        identified_count = 0
        skipped_count = 0
        
        for lg in unknown_locations:
            rep = lg.representative_component
            
            self.stdout.write(f"\\n--- Processing LocationGroup {lg.id} ---")
            self.stdout.write(f"Location: {lg.location}")
            self.stdout.write(f"Postcode: {rep.full_postcode}")
            
            if self.dry_run:
                self.stdout.write("DRY RUN: Would analyze with Places API")
                continue
            
            # Run smart business identification
            business_result = self.smart_identify_business(lg.location, rep.full_postcode)
            
            if business_result:
                action = business_result['action']
                
                if action == 'update':
                    self.stdout.write(f"✅ IDENTIFIED: {business_result['name']}")
                    self.stdout.write(f"   Confidence: {business_result['confidence']:.2f}")
                    self.stdout.write(f"   Reason: {business_result['reason']}")
                    
                    # Update representative component
                    rep.places_api_business_name = business_result['name']
                    rep.places_api_business_type = business_result.get('business_type')
                    rep.places_api_confidence = business_result['confidence']
                    rep.places_api_search_strategy = business_result['strategy']
                    rep.places_api_major_retailers = business_result.get('major_retailers', [])
                    rep.places_api_last_checked = timezone.now()
                    rep.save()
                    
                    # Update location name if it's a major retailer
                    if business_result.get('major_retailers'):
                        clean_name = self.clean_business_name(business_result['name'])
                        new_location = f"{clean_name}, {lg.location}"
                        
                        # Ensure it's not too long
                        if len(new_location) > 255:
                            new_location = new_location[:252] + "..."
                        
                        old_location = lg.location
                        lg.location = new_location
                        lg.save()
                        
                        # Update all components
                        Component.objects.filter(location=old_location).update(location=new_location)
                        
                        self.stdout.write(f"   Updated location: {new_location}")
                    
                    identified_count += 1
                    
                elif action == 'flag':
                    self.stdout.write(f"🔍 FLAGGED: {business_result['name']}")
                    self.stdout.write(f"   Reason: {business_result['reason']}")
                    
                    # Store for audit but don't update location name
                    rep.places_api_business_name = business_result['name']
                    rep.places_api_business_type = business_result.get('business_type')
                    rep.places_api_confidence = business_result['confidence']
                    rep.places_api_search_strategy = business_result['strategy'] + '_flagged'
                    rep.places_api_last_checked = timezone.now()
                    rep.save()
                    
                    skipped_count += 1
                    
            else:
                self.stdout.write("❌ No clear business identification found")
                
                # Mark as checked to avoid reprocessing
                rep.places_api_last_checked = timezone.now()
                rep.save()
                
                skipped_count += 1
            
            # Rate limiting
            time.sleep(self.delay)
        
        if not self.dry_run:
            self.stdout.write(f"\\n🎯 COMPLETE: Identified {identified_count} businesses, {skipped_count} skipped/flagged")
        else:
            self.stdout.write(f"\\nDRY RUN COMPLETE: Would process {total_count} locations")

    def smart_identify_business(self, location, postcode):
        """Smart business identification with decision matrix"""
        
        # Multi-strategy search
        strategies = [
            ('exact_address', location),
            ('postcode_area', f"{postcode} UK"),
            ('business_search', f"business {postcode} UK")
        ]
        
        all_results = []
        
        for strategy_name, query in strategies:
            self.stdout.write(f"   → {strategy_name}: {query}")
            results = self.call_places_api(query)
            
            if results:
                self.stdout.write(f"     Found {len(results)} result(s)")
                for i, result in enumerate(results[:3], 1):
                    name = result.get('name', 'Unknown')
                    types = result.get('types', [])
                    self.stdout.write(f"     {i}. {name} (Types: {types[:3]})")
                
                # Store results with strategy info
                for result in results[:3]:
                    result['search_strategy'] = strategy_name
                    all_results.append(result)
            else:
                self.stdout.write(f"     No results")
            
            time.sleep(0.2)  # Rate limiting between strategies
        
        if not all_results:
            return None
        
        # Apply decision matrix
        return self.apply_decision_matrix(all_results, location, postcode)

    def apply_decision_matrix(self, results, location, postcode):
        """Apply decision matrix to determine action"""
        
        first_result = results[0] if results else None
        
        # Decision Matrix Rules
        for result in results:
            name = result.get('name', '').lower()
            types = result.get('types', [])
            address = result.get('formatted_address', '')
            
            # Rule 1: Major retailer in first result with retail types
            major_retailers = self.identify_major_retailers(result.get('name', ''))
            is_retail = any(t in types for t in ['supermarket', 'grocery_or_supermarket', 'store', 'shopping_mall'])
            
            if major_retailers and is_retail:
                # Verify postcode matches
                if self.verify_postcode_match(address, postcode):
                    return {
                        'action': 'update',
                        'name': result.get('name'),
                        'business_type': 'retail',
                        'major_retailers': major_retailers,
                        'confidence': 0.9,
                        'strategy': result.get('search_strategy', 'unknown'),
                        'reason': f"Major retailer {major_retailers[0]} with retail types and matching postcode"
                    }
                else:
                    return {
                        'action': 'flag',
                        'name': result.get('name'),
                        'business_type': 'retail',
                        'confidence': 0.6,
                        'strategy': result.get('search_strategy', 'unknown'),
                        'reason': f"Major retailer {major_retailers[0]} but postcode mismatch (may be nearby)"
                    }
            
            # Rule 2: Facility-specific identification
            facility_types = self.identify_facility_type(result.get('name', ''), types)
            if facility_types and self.matches_location_context(facility_types, location):
                return {
                    'action': 'update',
                    'name': result.get('name'),
                    'business_type': facility_types[0],
                    'confidence': 0.8,
                    'strategy': result.get('search_strategy', 'unknown'),
                    'reason': f"Facility type {facility_types[0]} matches location context"
                }
        
        # Rule 3: First result is generic/unclear
        if first_result:
            name = first_result.get('name', '')
            types = first_result.get('types', [])
            
            # Check if it's too generic
            if any(t in types for t in ['route', 'postal_code', 'political']):
                return {
                    'action': 'flag',
                    'name': name,
                    'confidence': 0.3,
                    'strategy': first_result.get('search_strategy', 'unknown'),
                    'reason': "Generic location result (road, postcode, etc.)"
                }
        
        return None

    def identify_major_retailers(self, business_name):
        """Identify major retailers from business name"""
        if not business_name:
            return []
        
        name_lower = business_name.lower()
        retailers = []
        
        major_retailers = {
            'asda': 'ASDA',
            'tesco': 'Tesco',
            'sainsbury': 'Sainsburys',
            'morrisons': 'Morrisons',
            'aldi': 'Aldi',
            'lidl': 'Lidl',
            'waitrose': 'Waitrose',
            'marks & spencer': 'M&S',
            'iceland': 'Iceland'
        }
        
        for key, retailer in major_retailers.items():
            if key in name_lower:
                retailers.append(retailer)
        
        return retailers

    def identify_facility_type(self, business_name, types):
        """Identify facility types from business name and types"""
        if not business_name:
            return []
        
        name_lower = business_name.lower()
        facility_types = []
        
        facilities = {
            'energy hub': 'energy_facility',
            'energy centre': 'energy_facility',
            'power station': 'energy_facility',
            'water treatment': 'water_facility',
            'pumping station': 'water_facility',
            'treatment works': 'water_facility',
            'research centre': 'research_facility',
            'distribution centre': 'logistics_facility'
        }
        
        for key, facility_type in facilities.items():
            if key in name_lower:
                facility_types.append(facility_type)
        
        return facility_types

    def matches_location_context(self, facility_types, location):
        """Check if facility types match the location context"""
        location_lower = location.lower()
        
        context_matches = {
            'energy_facility': ['energy', 'power', 'electricity'],
            'water_facility': ['water', 'pumping', 'treatment'],
            'research_facility': ['research', 'centre', 'university'],
            'logistics_facility': ['distribution', 'depot', 'warehouse']
        }
        
        for facility_type in facility_types:
            if facility_type in context_matches:
                keywords = context_matches[facility_type]
                if any(keyword in location_lower for keyword in keywords):
                    return True
        
        return False

    def verify_postcode_match(self, api_address, expected_postcode):
        """Verify that the API address contains the expected postcode"""
        if not api_address or not expected_postcode:
            return False
        
        # Extract postcode from API address
        # UK postcodes have format like "SW1A 1AA" or "M1 1AA"
        postcode_pattern = r'[A-Z]{1,2}[0-9]{1,2}[A-Z]?\\s*[0-9][A-Z]{2}'
        api_postcodes = re.findall(postcode_pattern, api_address.upper())
        
        expected_clean = expected_postcode.upper().replace(' ', '')
        
        for api_postcode in api_postcodes:
            api_clean = api_postcode.replace(' ', '')
            if api_clean == expected_clean:
                return True
        
        return False

    def call_places_api(self, query):
        """Make Places API call and return results"""
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': query,
            'key': settings.GOOGLE_MAPS_API_KEY,
            'fields': 'name,business_status,rating,types,place_id,formatted_address'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                return data.get('results', [])
            
            return []
            
        except Exception as e:
            self.stdout.write(f"   API Error: {str(e)}")
            return []

    def clean_business_name(self, business_name):
        """Clean business name for location display"""
        if not business_name:
            return "Business"
        
        # Remove common suffixes
        name = business_name.replace("Superstore", "").replace("Supercentre", "").replace("Supermarket", "")
        name = name.replace("Store", "").strip()
        
        # Remove trailing comma
        if name.endswith(","):
            name = name[:-1].strip()
        
        return name or business_name