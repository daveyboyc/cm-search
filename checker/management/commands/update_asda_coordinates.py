"""
Management command to update ASDA store coordinates using Google Places API data.
Uses the Place ID from previous searches to get exact coordinates.
"""
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from checker.models import LocationGroup, Component
from django.db.models import Q


class Command(BaseCommand):
    help = 'Update geocoding coordinates for ASDA stores using Google Places API'

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

        self.stdout.write("=== UPDATING ASDA STORE COORDINATES FROM PLACES API ===")
        
        # Find ASDA locations with business information
        asda_locations = LocationGroup.objects.filter(
            Q(location__icontains='asda') | 
            Q(representative_component__places_api_major_retailers__contains=['ASDA'])
        ).select_related('representative_component')
        
        if options['limit']:
            asda_locations = asda_locations[:options['limit']]
        
        total_count = asda_locations.count()
        self.stdout.write(f"Found {total_count} ASDA locations to update coordinates")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        updated_count = 0
        failed_count = 0
        
        for lg in asda_locations:
            rep = lg.representative_component
            if not rep or not rep.places_api_business_name:
                continue
                
            self.stdout.write(f"\n--- Processing LocationGroup {lg.id} ---")
            self.stdout.write(f"Location: {lg.location}")
            self.stdout.write(f"Business: {rep.places_api_business_name}")
            self.stdout.write(f"Current coords: {rep.latitude}, {rep.longitude}")
            
            if self.dry_run:
                self.stdout.write("DRY RUN: Would fetch coordinates from Places API")
                continue
            
            # Get coordinates using Places API
            coords = self.get_place_coordinates(
                rep.places_api_business_name,
                rep.full_postcode
            )
            
            if coords:
                old_lat, old_lng = rep.latitude, rep.longitude
                new_lat, new_lng = coords['lat'], coords['lng']
                
                # Calculate distance moved (approximate)
                distance = 0
                if old_lat and old_lng:
                    distance = self.calculate_distance(old_lat, old_lng, new_lat, new_lng)
                    self.stdout.write(f"Distance moved: {distance:.2f} meters")
                
                # Safety check - don't move more than 10km unless no previous coordinates
                if old_lat and old_lng and distance > 10000:
                    self.stdout.write(f"⚠️ WARNING: Large movement detected ({distance:.0f}m) - skipping update")
                    self.stdout.write(f"   This might be a different ASDA or incorrect match")
                    failed_count += 1
                    continue
                
                # Update the representative component
                rep.latitude = new_lat
                rep.longitude = new_lng
                rep.geocoded = True
                rep.save()
                
                # Update the LocationGroup
                lg.latitude = new_lat
                lg.longitude = new_lng
                lg.save()
                
                # Update all components at this location
                Component.objects.filter(location=lg.location).update(
                    latitude=new_lat,
                    longitude=new_lng,
                    geocoded=True
                )
                
                self.stdout.write(f"✅ Updated coordinates: ({old_lat}, {old_lng}) → ({new_lat}, {new_lng})")
                updated_count += 1
            else:
                self.stdout.write("❌ Failed to get coordinates from Places API")
                failed_count += 1
            
            # Rate limiting
            time.sleep(self.delay)
        
        if not self.dry_run:
            self.stdout.write(f"\n🎯 COMPLETE: Updated {updated_count} ASDA locations, {failed_count} failed")
        else:
            self.stdout.write(f"\nDRY RUN COMPLETE: Would update {total_count} locations")

    def get_place_coordinates(self, business_name, postcode):
        """Get exact coordinates for a place using Google Places API"""
        
        # First, search for the place
        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        search_params = {
            'query': f"{business_name} {postcode} UK",
            'key': settings.GOOGLE_MAPS_API_KEY,
        }
        
        try:
            response = requests.get(search_url, params=search_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                # Find the best match (prioritize exact name matches)
                best_result = None
                for result in data['results']:
                    if business_name.lower() in result.get('name', '').lower():
                        best_result = result
                        break
                
                if not best_result:
                    best_result = data['results'][0]
                
                # Extract coordinates
                location = best_result.get('geometry', {}).get('location', {})
                if location:
                    return {
                        'lat': location.get('lat'),
                        'lng': location.get('lng'),
                        'place_id': best_result.get('place_id'),
                        'name': best_result.get('name')
                    }
            
            return None
            
        except Exception as e:
            self.stdout.write(f"   API Error: {str(e)}")
            return None

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate approximate distance between two coordinates in meters"""
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