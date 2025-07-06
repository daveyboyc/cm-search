"""
Management command to update Oaktree Power locations as Boots stores.
Uses Places API to get exact store names and coordinates.
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
    help = 'Update Oaktree Power locations as Boots stores using Places API'

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

        self.stdout.write("=== UPDATING OAKTREE POWER LOCATIONS AS BOOTS STORES ===")
        
        # Find Oaktree Power locations with 'commercial sites' description
        oaktree_locations = LocationGroup.objects.filter(
            companies__icontains='oaktree',
            descriptions__icontains='commercial sites'
        ).select_related('representative_component')
        
        if options['limit']:
            oaktree_locations = oaktree_locations[:options['limit']]
        
        total_count = oaktree_locations.count()
        self.stdout.write(f"Found {total_count} Oaktree Power locations to update")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        boots_identified = 0
        non_boots_found = 0
        failed_count = 0
        
        for lg in oaktree_locations:
            rep = lg.representative_component
            
            self.stdout.write(f"\\n--- Processing LocationGroup {lg.id} ---")
            self.stdout.write(f"Location: {lg.location}")
            self.stdout.write(f"Postcode: {rep.full_postcode if rep else 'None'}")
            
            if self.dry_run:
                self.stdout.write("DRY RUN: Would search Places API for Boots store")
                continue
            
            # Get Boots store information from Places API
            boots_result = self.get_boots_store_info(lg.location, rep.full_postcode if rep else '')
            
            if boots_result and boots_result['is_boots']:
                self.stdout.write(f"✅ BOOTS FOUND: {boots_result['name']}")
                
                # Update representative component with Boots information
                old_business = rep.places_api_business_name
                rep.places_api_business_name = boots_result['name']
                rep.places_api_business_type = 'pharmacy'
                rep.places_api_major_retailers = ['Boots']
                rep.places_api_confidence = 0.95
                rep.places_api_search_strategy = 'oaktree_boots_identification'
                rep.places_api_last_checked = timezone.now()
                
                # Update coordinates if available
                if boots_result.get('coordinates'):
                    old_lat, old_lng = rep.latitude, rep.longitude
                    new_lat, new_lng = boots_result['coordinates']['lat'], boots_result['coordinates']['lng']
                    
                    # Calculate distance moved if we have old coordinates
                    if old_lat and old_lng:
                        distance = self.calculate_distance(old_lat, old_lng, new_lat, new_lng)
                        self.stdout.write(f"   Distance moved: {distance:.2f} meters")
                        
                        # Safety check - don't move more than 5km for Boots stores
                        if distance > 5000:
                            self.stdout.write(f"   ⚠️ WARNING: Large movement detected ({distance:.0f}m) - skipping coordinate update")
                        else:
                            rep.latitude = new_lat
                            rep.longitude = new_lng
                            rep.geocoded = True
                            
                            # Update LocationGroup coordinates
                            lg.latitude = new_lat
                            lg.longitude = new_lng
                            
                            self.stdout.write(f"   Updated coordinates: ({old_lat}, {old_lng}) → ({new_lat}, {new_lng})")
                    else:
                        # No previous coordinates, set new ones
                        rep.latitude = new_lat
                        rep.longitude = new_lng
                        rep.geocoded = True
                        lg.latitude = new_lat
                        lg.longitude = new_lng
                        self.stdout.write(f"   Set coordinates: ({new_lat}, {new_lng})")
                
                rep.save()
                
                # Update location name to include Boots branding
                old_location = lg.location
                new_location = self.create_boots_location_name(boots_result['name'], old_location, rep.full_postcode if rep else '')
                
                if new_location != old_location:
                    lg.location = new_location
                    lg.save()
                    
                    # Update all components at this location
                    updated_components = Component.objects.filter(location=old_location).update(
                        location=new_location
                    )
                    
                    self.stdout.write(f"   Location: '{old_location}' → '{new_location}'")
                    self.stdout.write(f"   Updated {updated_components} components")
                else:
                    lg.save()  # Save coordinate updates
                
                boots_identified += 1
                
            elif boots_result and not boots_result['is_boots']:
                self.stdout.write(f"🔍 NON-BOOTS FOUND: {boots_result['name']}")
                self.stdout.write(f"   This location may not be a Boots store")
                
                # Still update with what we found for audit purposes
                rep.places_api_business_name = boots_result['name']
                rep.places_api_business_type = 'unknown'
                rep.places_api_confidence = 0.5
                rep.places_api_search_strategy = 'oaktree_non_boots'
                rep.places_api_last_checked = timezone.now()
                rep.save()
                
                non_boots_found += 1
                
            else:
                self.stdout.write("❌ No clear business found via Places API")
                
                # Mark as checked to avoid reprocessing
                if rep:
                    rep.places_api_last_checked = timezone.now()
                    rep.save()
                
                failed_count += 1
            
            # Rate limiting
            time.sleep(self.delay)
        
        if not self.dry_run:
            self.stdout.write(f"\\n🎯 COMPLETE:")
            self.stdout.write(f"   ✅ Boots stores identified: {boots_identified}")
            self.stdout.write(f"   🔍 Non-Boots found: {non_boots_found}")
            self.stdout.write(f"   ❌ Failed/No results: {failed_count}")
        else:
            self.stdout.write(f"\\nDRY RUN COMPLETE: Would process {total_count} locations")

    def get_boots_store_info(self, location, postcode):
        """Get Boots store information from Places API"""
        
        # Since we know they're all Boots stores, prioritize Boots-specific searches
        search_queries = [
            f"Boots {postcode} UK" if postcode else None,  # Start with Boots + postcode
            f"Boots pharmacy {postcode} UK" if postcode else None,  # Try Boots pharmacy
            location,  # Try full location as fallback
            f"{postcode} UK" if postcode else None,  # General postcode search as last resort
        ]
        
        # Remove None values
        search_queries = [q for q in search_queries if q]
        
        for query in search_queries:
            self.stdout.write(f"   → Searching: {query}")
            
            results = self.call_places_api(query)
            if results:
                # Look for Boots in first few results, not just the first one
                for i, result in enumerate(results[:3]):
                    business_name = result.get('name', '')
                    self.stdout.write(f"     Result {i+1}: {business_name}")
                    
                    # Check if it's a Boots store
                    is_boots = 'boots' in business_name.lower()
                    
                    if is_boots:
                        self.stdout.write(f"     ✅ Found Boots: {business_name}")
                        
                        result_info = {
                            'name': business_name,
                            'is_boots': True,
                            'types': result.get('types', []),
                            'address': result.get('formatted_address', ''),
                        }
                        
                        # Get coordinates
                        location_data = result.get('geometry', {}).get('location', {})
                        if location_data:
                            result_info['coordinates'] = {
                                'lat': location_data.get('lat'),
                                'lng': location_data.get('lng')
                            }
                        
                        return result_info
                
                # If no Boots found in this query, continue to next query
                self.stdout.write(f"     No Boots found in results")
            
            time.sleep(0.2)  # Rate limiting between queries
        
        # If we still haven't found Boots, return the first result but mark as non-Boots
        # This shouldn't happen often since we know they're all Boots stores
        if search_queries:
            final_results = self.call_places_api(search_queries[0])
            if final_results:
                first_result = final_results[0]
                return {
                    'name': first_result.get('name', ''),
                    'is_boots': False,
                    'types': first_result.get('types', []),
                    'address': first_result.get('formatted_address', ''),
                }
        
        return None

    def call_places_api(self, query):
        """Make Places API call and return results"""
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': query,
            'key': settings.GOOGLE_MAPS_API_KEY,
            'fields': 'name,business_status,rating,types,place_id,formatted_address,geometry'
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

    def create_boots_location_name(self, boots_name, original_location, postcode):
        """Create a new location name that includes Boots branding"""
        
        # Extract the Boots store identifier (e.g., "Boots Wimbledon" -> "Wimbledon")
        boots_clean = boots_name.replace("Boots", "").strip()
        if boots_clean.startswith("Pharmacy"):
            boots_clean = boots_clean.replace("Pharmacy", "").strip()
        
        # If we got a clean location identifier, use it
        if boots_clean:
            # Try to extract meaningful address parts from original location
            # Remove Oaktree-specific prefixes and suffixes
            original_clean = original_location
            
            # Remove common Oaktree patterns
            original_clean = re.sub(r'^[^A-Za-z]*', '', original_clean)  # Remove leading numbers/symbols
            original_clean = re.sub(r' - [^,]+$', '', original_clean)  # Remove " - Region" suffix
            
            # Extract postcode if present in original
            if postcode and postcode in original_clean:
                # Keep the part that has the postcode
                if postcode in original_clean:
                    address_parts = original_clean.split(postcode)
                    if len(address_parts) > 0:
                        address_base = address_parts[0].strip().rstrip(',').strip()
                        return f"Boots {boots_clean}, {address_base}, {postcode}"
            
            # Fallback: use original location with Boots prefix
            return f"Boots {boots_clean}, {original_clean}"
        
        # If we couldn't extract clean name, just prefix with Boots
        return f"Boots, {original_location}"

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in meters using Haversine formula"""
        from math import radians, cos, sin, sqrt, atan2
        
        R = 6371000  # Earth's radius in meters
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        # Haversine formula
        a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c