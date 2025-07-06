"""
Management command to test Google Places API for business detection.
Focuses on identifying ASDA stores in Flexitricity DSR entries.
"""
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from checker.models import Component
from django.db.models import Q
import re


class Command(BaseCommand):
    help = 'Test Google Places API to identify businesses (focusing on ASDA stores)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['validate', 'test', 'full', 'flexiload', 'single'],
            default='validate',
            help='Mode: validate (known ASDA), test (candidates), full (all Flexitricity), flexiload (Flexitricity with load descriptions), single (test single address)'
        )
        parser.add_argument(
            '--address',
            type=str,
            help='Single address to test (use with --mode single)'
        )
        parser.add_argument(
            '--postcode',
            type=str,
            help='Postcode for single address test (use with --mode single)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of locations to process'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between API requests in seconds'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making API calls'
        )

    def handle(self, *args, **options):
        self.delay = options['delay']
        self.dry_run = options['dry_run']
        
        # Check API key
        if not hasattr(settings, 'GOOGLE_MAPS_API_KEY') or not settings.GOOGLE_MAPS_API_KEY:
            self.stdout.write(
                self.style.ERROR('GOOGLE_MAPS_API_KEY not configured in settings')
            )
            return

        self.stdout.write(f"Starting Places API test in '{options['mode']}' mode")
        
        if options['mode'] == 'validate':
            self.validate_known_asda(options['limit'])
        elif options['mode'] == 'test':
            self.test_asda_candidates(options['limit'])
        elif options['mode'] == 'full':
            self.process_all_flexitricity(options['limit'])
        elif options['mode'] == 'flexiload':
            self.test_flexitricity_load(options['limit'])
        elif options['mode'] == 'single':
            self.test_single_address(options['address'], options['postcode'])

    def validate_known_asda(self, limit):
        """Test API with known ASDA entries to validate approach"""
        self.stdout.write("=== VALIDATION MODE: Testing known ASDA entries ===")
        
        # Get known ASDA entries with postcodes
        asda_entries = Component.objects.filter(
            Q(location__icontains='asda') | Q(description__icontains='asda'),
            full_postcode__isnull=False
        ).exclude(
            places_api_last_checked__isnull=False
        )[:limit]
        
        self.stdout.write(f"Found {asda_entries.count()} known ASDA entries to validate")
        
        for component in asda_entries:
            self.process_component(component, expected_business="ASDA")

    def test_asda_candidates(self, limit):
        """Test API with high-probability ASDA candidates"""
        self.stdout.write("=== TEST MODE: Testing ASDA candidates ===")
        
        # Find Flexitricity DSR components likely to be ASDA
        candidates = Component.objects.filter(
            company_name__icontains='flexitricity',
            technology__icontains='DSR',
            description__icontains='refrigeration',
            full_postcode__isnull=False
        ).exclude(
            Q(location__icontains='asda') |
            Q(description__icontains='asda') |
            Q(places_api_last_checked__isnull=False)
        )[:limit]
        
        self.stdout.write(f"Found {candidates.count()} ASDA candidates to test")
        
        for component in candidates:
            self.process_component(component, expected_business="ASDA (candidate)")

    def process_all_flexitricity(self, limit):
        """Process all Flexitricity entries for business detection"""
        self.stdout.write("=== FULL MODE: Processing all Flexitricity entries ===")
        
        all_flexitricity = Component.objects.filter(
            company_name__icontains='flexitricity',
            full_postcode__isnull=False
        ).exclude(
            places_api_last_checked__isnull=False
        )[:limit]
        
        self.stdout.write(f"Found {all_flexitricity.count()} Flexitricity entries to process")
        
        for component in all_flexitricity:
            self.process_component(component)

    def test_flexitricity_load(self, limit):
        """Test Flexitricity LocationGroups with 'load' in description"""
        self.stdout.write("=== FLEXILOAD MODE: Testing Flexitricity locations with 'load' descriptions ===")
        
        from checker.models import LocationGroup
        
        # Find Flexitricity LocationGroups with 'load' in description
        flexi_load = LocationGroup.objects.filter(
            companies__icontains='flexitricity',
            descriptions__icontains='load',
            representative_component__full_postcode__isnull=False
        ).exclude(
            representative_component__places_api_last_checked__isnull=False
        )[:limit]
        
        self.stdout.write(f"Found {flexi_load.count()} Flexitricity LocationGroups with 'load' descriptions")
        
        # Group by description pattern for better analysis
        patterns = {}
        for lg in flexi_load:
            first_desc = lg.descriptions[0] if lg.descriptions else 'No description'
            pattern_key = self.categorize_description(first_desc)
            if pattern_key not in patterns:
                patterns[pattern_key] = []
            patterns[pattern_key].append(lg)
        
        self.stdout.write(f"\nDescription patterns found:")
        for pattern, locations in patterns.items():
            self.stdout.write(f"  {pattern}: {len(locations)} locations")
        
        # Track results for summary
        summary_results = []
        
        # Process each location
        for lg in flexi_load:
            result = self.process_location_group_with_summary(lg)
            if result:
                summary_results.append(result)
        
        # Print summary table
        self.print_summary_table(summary_results)

    def test_single_address(self, address, postcode):
        """Test a single address with enhanced search"""
        if not address or not postcode:
            self.stdout.write(self.style.ERROR('Both --address and --postcode are required for single mode'))
            return
        
        self.stdout.write("=== SINGLE ADDRESS MODE ===")
        self.stdout.write(f"Testing: {address}")
        self.stdout.write(f"Postcode: {postcode}")
        self.stdout.write("="*50)
        
        if self.dry_run:
            self.stdout.write("DRY RUN: Would call Places API here")
            return
        
        # Use enhanced search
        result = self.search_places_api_enhanced(address, postcode)
        
        if result:
            self.stdout.write(f"\n✅ FINAL RESULT:")
            self.stdout.write(f"   Business: {result.get('name', 'Unknown')}")
            self.stdout.write(f"   Strategy: {result.get('strategy', 'Unknown')}")
            self.stdout.write(f"   Confidence: {result.get('confidence', 0):.2f}")
            self.stdout.write(f"   Types: {', '.join(result.get('types', [])[:3])}")
            
            if 'major_retailers' in result and result['major_retailers']:
                self.stdout.write(f"   🏪 Major Retailers: {', '.join(result['major_retailers'])}")
            
            # Check specifically for ASDA
            if 'asda' in result.get('name', '').lower():
                self.stdout.write(f"   🎯 ASDA CONFIRMED!")
            else:
                self.stdout.write(f"   ❌ No ASDA detected in primary result")
        else:
            self.stdout.write(f"\n❌ No businesses found at this address")

    def process_component(self, component, expected_business=None):
        """Process a single component with Places API"""
        self.stdout.write(f"\n--- Processing Component {component.id} ---")
        self.stdout.write(f"Location: {component.location}")
        self.stdout.write(f"Postcode: {component.full_postcode}")
        if expected_business:
            self.stdout.write(f"Expected: {expected_business}")
        
        if self.dry_run:
            self.stdout.write("DRY RUN: Would call Places API here")
            return
        
        # Call Places API
        business_info = self.search_places_api(component.location, component.full_postcode)
        
        if business_info:
            self.stdout.write(f"✅ Found business: {business_info['name']}")
            self.stdout.write(f"   Confidence: {business_info['confidence']:.2f}")
            self.stdout.write(f"   Types: {', '.join(business_info.get('types', []))}")
            
            # Update component
            component.places_api_business_name = business_info['name']
            component.places_api_confidence = business_info['confidence']
            component.places_api_last_checked = timezone.now()
            component.save()
            
            # Check if it's ASDA
            if 'asda' in business_info['name'].lower():
                self.stdout.write(f"🎯 ASDA STORE DETECTED: {business_info['name']}")
        else:
            self.stdout.write("❌ No business found")
            
            # Still mark as checked to avoid re-processing
            component.places_api_last_checked = timezone.now()
            component.save()
        
        # Rate limiting
        time.sleep(self.delay)

    def process_location_group(self, location_group):
        """Process a LocationGroup (not individual component)"""
        self.stdout.write(f"\n--- Processing LocationGroup {location_group.id} ---")
        self.stdout.write(f"Location: {location_group.location}")
        
        if location_group.representative_component:
            postcode = location_group.representative_component.full_postcode
            self.stdout.write(f"Postcode: {postcode}")
            
            # Show description pattern
            first_desc = location_group.descriptions[0] if location_group.descriptions else 'No description'
            pattern = self.categorize_description(first_desc)
            self.stdout.write(f"Pattern: {pattern}")
            self.stdout.write(f"Description: {first_desc}")
            
            if self.dry_run:
                self.stdout.write("DRY RUN: Would call Places API here")
                return
            
            # Use enhanced search with multiple strategies
            business_info = self.search_places_api_enhanced(location_group.location, postcode)
            
            if business_info:
                self.stdout.write(f"✅ Found business: {business_info['name']}")
                self.stdout.write(f"   Confidence: {business_info['confidence']:.2f}")
                self.stdout.write(f"   Types: {', '.join(business_info.get('types', [])[:5])}")
                self.stdout.write(f"   Strategy: {business_info.get('strategy', 'unknown')}")
                
                # Update representative component
                rep_comp = location_group.representative_component
                rep_comp.places_api_business_name = business_info['name']
                rep_comp.places_api_confidence = business_info['confidence']
                rep_comp.places_api_last_checked = timezone.now()
                rep_comp.save()
                
                # Check for major retailers
                retailer = self.identify_major_retailer(business_info['name'])
                if retailer:
                    self.stdout.write(f"🏪 MAJOR RETAILER DETECTED: {retailer}")
            else:
                self.stdout.write("❌ No business found with any strategy")
                
                # Still mark as checked
                rep_comp = location_group.representative_component
                rep_comp.places_api_last_checked = timezone.now()
                rep_comp.save()
        
        # Rate limiting
        time.sleep(self.delay)

    def process_location_group_with_summary(self, location_group):
        """Process a LocationGroup and return summary data"""
        self.stdout.write(f"\n--- Processing LocationGroup {location_group.id} ---")
        self.stdout.write(f"Location: {location_group.location}")
        
        if location_group.representative_component:
            postcode = location_group.representative_component.full_postcode
            self.stdout.write(f"Postcode: {postcode}")
            
            # Show description pattern
            first_desc = location_group.descriptions[0] if location_group.descriptions else 'No description'
            pattern = self.categorize_description(first_desc)
            self.stdout.write(f"Pattern: {pattern}")
            self.stdout.write(f"Description: {first_desc}")
            
            if self.dry_run:
                self.stdout.write("DRY RUN: Would call Places API here")
                return None
            
            # Use enhanced search with multiple strategies
            business_info = self.search_places_api_enhanced(location_group.location, postcode)
            
            # Create summary result
            summary_result = {
                'address': location_group.location,
                'postcode': postcode,
                'businesses': [],
                'major_retailers': [],
                'total_businesses': 0
            }
            
            if business_info:
                # Use the data from the enhanced search result
                summary_result['total_businesses'] = business_info.get('total_businesses', 1)
                summary_result['major_retailers'] = business_info.get('major_retailers', [])
                
                # Add the primary business name found
                summary_result['businesses'].append(business_info.get('name', ''))
                
                # Update representative component with enhanced data
                rep_comp = location_group.representative_component
                rep_comp.places_api_business_name = business_info['name']
                rep_comp.places_api_confidence = business_info['confidence']
                rep_comp.places_api_search_strategy = business_info.get('strategy', 'unknown')
                rep_comp.places_api_major_retailers = business_info.get('major_retailers', [])
                
                # Store primary business type from the result
                business_types = business_info.get('types', [])
                if business_types:
                    rep_comp.places_api_business_type = business_types[0]  # Store first/primary type
                
                rep_comp.places_api_last_checked = timezone.now()
                rep_comp.save()
                
            else:
                # Still mark as checked
                rep_comp = location_group.representative_component
                rep_comp.places_api_last_checked = timezone.now()
                rep_comp.save()
            
            # Rate limiting
            time.sleep(self.delay)
            
            return summary_result
        
        return None

    def print_summary_table(self, results):
        """Print a formatted summary table of all results"""
        self.stdout.write("\n" + "="*120)
        self.stdout.write("SUMMARY TABLE - FLEXITRICITY LOCATIONS WITH 'LOAD' DESCRIPTIONS")
        self.stdout.write("="*120)
        
        # Count statistics
        total_locations = len(results)
        locations_with_businesses = len([r for r in results if r['total_businesses'] > 0])
        locations_with_multiple = len([r for r in results if r['total_businesses'] > 1])
        
        asda_locations = len([r for r in results if 'ASDA' in r['major_retailers']])
        all_retailers = []
        for r in results:
            all_retailers.extend(r['major_retailers'])
        retailer_counts = {}
        for retailer in all_retailers:
            retailer_counts[retailer] = retailer_counts.get(retailer, 0) + 1
        
        self.stdout.write(f"\nSTATISTICS:")
        self.stdout.write(f"Total locations tested: {total_locations}")
        self.stdout.write(f"Locations with businesses found: {locations_with_businesses}")
        self.stdout.write(f"Locations with multiple businesses: {locations_with_multiple}")
        self.stdout.write(f"ASDA stores found: {asda_locations}")
        
        if retailer_counts:
            self.stdout.write(f"\nMAJOR RETAILERS FOUND:")
            for retailer, count in sorted(retailer_counts.items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"  {retailer}: {count} locations")
        
        self.stdout.write(f"\nDETAILED RESULTS:")
        self.stdout.write("-"*120)
        
        # Print header
        header = f"{'Address':<50} {'Postcode':<10} {'Businesses':<8} {'Major Retailers':<20} {'Business Names':<30}"
        self.stdout.write(header)
        self.stdout.write("-"*120)
        
        # Sort by major retailers first, then by number of businesses
        sorted_results = sorted(results, key=lambda x: (len(x['major_retailers']) == 0, -x['total_businesses'], x['address']))
        
        for result in sorted_results:
            address = result['address'][:47] + "..." if len(result['address']) > 50 else result['address']
            postcode = result['postcode'] or 'N/A'
            business_count = str(result['total_businesses'])
            retailers = ', '.join(result['major_retailers']) if result['major_retailers'] else '-'
            retailers = retailers[:17] + "..." if len(retailers) > 20 else retailers
            
            # Show first 2 business names
            business_names = ', '.join(result['businesses'][:2])
            if len(result['businesses']) > 2:
                business_names += f" (+{len(result['businesses'])-2} more)"
            business_names = business_names[:27] + "..." if len(business_names) > 30 else business_names
            
            row = f"{address:<50} {postcode:<10} {business_count:<8} {retailers:<20} {business_names:<30}"
            self.stdout.write(row)
        
        self.stdout.write("="*120)

    def search_places_api(self, location, postcode):
        """Search Google Places API for business at given location"""
        # Clean up location for search
        search_query = f"{location} {postcode} UK"
        
        # Remove extra spaces and clean up
        search_query = re.sub(r'\s+', ' ', search_query.strip())
        
        self.stdout.write(f"   API Query: {search_query}")
        
        # Places API Text Search endpoint
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': search_query,
            'key': settings.GOOGLE_MAPS_API_KEY,
            'type': 'store',  # Focus on retail stores
            'fields': 'name,business_status,rating,types,place_id'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'OK':
                self.stdout.write(f"   API Error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                return None
            
            results = data.get('results', [])
            if not results:
                return None
            
            # Analyze first result
            result = results[0]
            business_name = result.get('name', '')
            business_types = result.get('types', [])
            
            # Calculate confidence score
            confidence = self.calculate_confidence(location, postcode, business_name, business_types)
            
            return {
                'name': business_name,
                'confidence': confidence,
                'types': business_types,
                'place_id': result.get('place_id', ''),
                'business_status': result.get('business_status', ''),
                'rating': result.get('rating')
            }
            
        except requests.RequestException as e:
            self.stdout.write(f"   Request Error: {e}")
            return None
        except Exception as e:
            self.stdout.write(f"   Unexpected Error: {e}")
            return None

    def calculate_confidence(self, location, postcode, business_name, business_types):
        """Calculate confidence score for business match"""
        confidence = 0.0
        
        # Base confidence for finding any business
        confidence += 0.3
        
        # Boost for retail/store types
        retail_types = ['store', 'establishment', 'supermarket', 'grocery_or_supermarket']
        if any(t in business_types for t in retail_types):
            confidence += 0.2
        
        # Boost for known retailers
        known_retailers = ['asda', 'tesco', 'sainsbury', 'morrisons', 'iceland', 'aldi', 'lidl']
        business_lower = business_name.lower()
        for retailer in known_retailers:
            if retailer in business_lower:
                confidence += 0.4
                break
        
        # Postcode proximity boost (if we had more sophisticated matching)
        if postcode and postcode.replace(' ', '').upper() in business_name.upper():
            confidence += 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0

    def search_places_api_enhanced(self, location, postcode):
        """Enhanced multi-strategy search prioritizing ASDA detection"""
        
        # Define search strategies in priority order for ASDA detection
        search_strategies = [
            ('asda_specific', f"ASDA {location} {postcode} UK"),
            ('asda_postcode', f"ASDA {postcode} UK"),
            ('supermarket_address', f"supermarket {location} {postcode}"),
            ('store_address', f"store {location} {postcode}"),
            ('full_address', f"{location} {postcode} UK"),
            ('business_postcode', f"business {postcode} UK")
        ]
        
        all_results = []
        asda_result = None
        best_result = None
        
        self.stdout.write(f"   Multi-strategy search for: {location}")
        
        for strategy_name, query in search_strategies:
            self.stdout.write(f"   → Trying {strategy_name}: {query}")
            
            results = self.call_places_api_raw(query)
            if results:
                self.stdout.write(f"     Found {len(results)} result(s)")
                
                # Check first few results for ASDA
                for result in results[:3]:
                    business_name = result.get('name', '')
                    if 'asda' in business_name.lower():
                        self.stdout.write(f"     🎯 ASDA FOUND: {business_name}")
                        asda_result = result
                        asda_result['strategy'] = strategy_name
                        asda_result['confidence'] = 0.95
                        break
                
                # Store all results for analysis
                for result in results:
                    result['strategy'] = strategy_name
                    all_results.append(result)
                
                # If we found ASDA, we can stop searching
                if asda_result:
                    break
                    
                # Keep best non-ASDA result as fallback
                if not best_result and results:
                    best_result = results[0]
                    best_result['strategy'] = strategy_name
                    best_result['confidence'] = 0.7
            else:
                self.stdout.write(f"     No results")
            
            # Small delay between API calls
            time.sleep(0.3)
        
        # Return ASDA result if found, otherwise best result
        final_result = asda_result or best_result
        
        if final_result:
            # Analyze all businesses found at this location
            unique_businesses = {}
            major_retailers = []
            
            for result in all_results:
                name = result.get('name', '')
                if name and name not in unique_businesses:
                    unique_businesses[name] = result
                    retailer = self.identify_major_retailer(name)
                    if retailer and retailer not in major_retailers:
                        major_retailers.append(retailer)
            
            self.stdout.write(f"   📍 Total unique businesses found: {len(unique_businesses)}")
            
            # Show top businesses
            for i, (name, result) in enumerate(list(unique_businesses.items())[:5]):
                types = ', '.join(result.get('types', [])[:3])
                retailer = self.identify_major_retailer(name)
                retailer_info = f" 🏪 {retailer}" if retailer else ""
                self.stdout.write(f"     {i+1}. {name} ({types}){retailer_info}")
            
            if len(unique_businesses) > 5:
                self.stdout.write(f"     ... and {len(unique_businesses) - 5} more")
            
            if major_retailers:
                self.stdout.write(f"   🎯 MAJOR RETAILERS: {', '.join(major_retailers)}")
            
            final_result['total_businesses'] = len(unique_businesses)
            final_result['major_retailers'] = major_retailers
            return final_result
        
        self.stdout.write(f"   ❌ No businesses found with any strategy")
        return None

    def call_places_api_raw(self, query):
        """Make raw Places API call and return all results"""
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        # Clean up query
        search_query = re.sub(r'\s+', ' ', query.strip())
        
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
                return results  # Return all results
            
            return []
            
        except Exception:
            return []

    def score_business_result(self, result, location, postcode):
        """Score a business result based on relevance and type"""
        business_name = result.get('name', '').lower()
        business_types = result.get('types', [])
        rating = result.get('rating', 0)
        
        score = 0.3  # Base score for finding any business
        
        # Major retailer bonus (highest priority)
        major_retailers = ['asda', 'tesco', 'sainsbury', 'morrisons', 'iceland', 'aldi', 'lidl', 'waitrose']
        for retailer in major_retailers:
            if retailer in business_name:
                score += 0.6
                break
        
        # Supermarket/grocery types bonus
        grocery_types = ['supermarket', 'grocery_or_supermarket', 'food']
        if any(t in business_types for t in grocery_types):
            score += 0.2
        
        # Store types bonus
        store_types = ['store', 'establishment']
        if any(t in business_types for t in store_types):
            score += 0.1
        
        # Rating bonus (businesses with ratings are more legitimate)
        if rating and rating > 0:
            score += 0.1
        
        # Penalty for generic/irrelevant results
        generic_terms = ['road', 'street', 'avenue', 'close', 'way']
        if any(term in business_name for term in generic_terms) and len(business_name.split()) <= 2:
            score -= 0.2
        
        return min(score, 1.0)

    def identify_major_retailer(self, business_name):
        """Identify if business name contains a major retailer"""
        if not business_name:
            return None
        
        name_lower = business_name.lower()
        
        retailers = {
            'asda': 'ASDA',
            'tesco': 'Tesco', 
            'sainsbury': 'Sainsbury\'s',
            'morrisons': 'Morrisons',
            'iceland': 'Iceland',
            'aldi': 'Aldi',
            'lidl': 'Lidl',
            'waitrose': 'Waitrose',
            'marks & spencer': 'M&S',
            'john lewis': 'John Lewis',
            'argos': 'Argos',
            'currys': 'Currys',
            'homebase': 'Homebase',
            'b&q': 'B&Q',
            'wickes': 'Wickes'
        }
        
        for key, display_name in retailers.items():
            if key in name_lower:
                return display_name
        
        return None

    def categorize_description(self, description):
        """Categorize description into patterns for analysis"""
        if not description:
            return 'No description'
        
        desc_lower = description.lower()
        
        if 'refrigeration' in desc_lower and 'curtailment' in desc_lower:
            return 'Load curtailment from refrigeration'
        elif 'load curtailment' in desc_lower:
            return 'Load curtailment (general)'
        elif 'load reduction' in desc_lower:
            return 'Load reduction'
        elif 'chp' in desc_lower:
            return 'CHP/Generation'
        elif 'horticultural' in desc_lower:
            return 'Horticultural'
        else:
            return 'Other load-related'

    def cleanup_old_checks(self):
        """Remove old API check timestamps to allow re-processing"""
        cutoff = timezone.now() - timezone.timedelta(days=7)
        updated = Component.objects.filter(
            places_api_last_checked__lt=cutoff
        ).update(places_api_last_checked=None)
        
        self.stdout.write(f"Cleared {updated} old API check timestamps")