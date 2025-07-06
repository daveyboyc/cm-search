"""
Audit system for business identifications made via Places API.
Helps review and validate business identification decisions.
"""
from django.core.management.base import BaseCommand
from checker.models import LocationGroup
from django.db.models import Q
from collections import defaultdict
import json


class Command(BaseCommand):
    help = 'Audit business identifications made via Places API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy',
            type=str,
            help='Filter by search strategy (e.g., asda_specific_fix, energy_facility_search)'
        )
        parser.add_argument(
            '--confidence',
            type=float,
            help='Filter by minimum confidence score'
        )
        parser.add_argument(
            '--retailer',
            type=str,
            help='Filter by major retailer (e.g., ASDA, Tesco)'
        )
        parser.add_argument(
            '--suspicious',
            action='store_true',
            help='Show potentially suspicious identifications'
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show summary statistics only'
        )

    def handle(self, *args, **options):
        self.stdout.write("=== BUSINESS IDENTIFICATION AUDIT ===")
        
        # Base query for locations with business information
        locations = LocationGroup.objects.filter(
            representative_component__places_api_business_name__isnull=False
        ).select_related('representative_component')
        
        # Apply filters
        if options['strategy']:
            locations = locations.filter(
                representative_component__places_api_search_strategy__icontains=options['strategy']
            )
        
        if options['confidence']:
            locations = locations.filter(
                representative_component__places_api_confidence__gte=options['confidence']
            )
        
        if options['retailer']:
            locations = locations.filter(
                representative_component__places_api_major_retailers__contains=[options['retailer']]
            )
        
        total_count = locations.count()
        self.stdout.write(f"Found {total_count} locations with business identifications")
        
        if options['summary']:
            self.show_summary(locations)
            return
        
        if options['suspicious']:
            self.show_suspicious(locations)
            return
        
        # Show detailed audit
        self.show_detailed_audit(locations)

    def show_summary(self, locations):
        """Show summary statistics"""
        self.stdout.write("\\n=== SUMMARY STATISTICS ===")
        
        # Group by search strategy
        strategies = defaultdict(int)
        retailers = defaultdict(int)
        business_types = defaultdict(int)
        confidence_ranges = defaultdict(int)
        
        for lg in locations:
            rep = lg.representative_component
            
            # Count strategies
            strategy = rep.places_api_search_strategy or 'unknown'
            strategies[strategy] += 1
            
            # Count retailers
            for retailer in rep.places_api_major_retailers or []:
                retailers[retailer] += 1
            
            # Count business types
            business_type = rep.places_api_business_type or 'unknown'
            business_types[business_type] += 1
            
            # Count confidence ranges
            confidence = rep.places_api_confidence or 0
            if confidence >= 0.9:
                confidence_ranges['High (0.9+)'] += 1
            elif confidence >= 0.7:
                confidence_ranges['Medium (0.7-0.9)'] += 1
            elif confidence >= 0.5:
                confidence_ranges['Low (0.5-0.7)'] += 1
            else:
                confidence_ranges['Very Low (<0.5)'] += 1
        
        self.stdout.write("\\n📊 Search Strategies:")
        for strategy, count in sorted(strategies.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"  {strategy}: {count}")
        
        self.stdout.write("\\n🏪 Major Retailers:")
        for retailer, count in sorted(retailers.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"  {retailer}: {count}")
        
        self.stdout.write("\\n🏢 Business Types:")
        for business_type, count in sorted(business_types.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"  {business_type}: {count}")
        
        self.stdout.write("\\n📈 Confidence Levels:")
        for confidence_range, count in sorted(confidence_ranges.items()):
            self.stdout.write(f"  {confidence_range}: {count}")

    def show_suspicious(self, locations):
        """Show potentially suspicious identifications"""
        self.stdout.write("\\n=== POTENTIALLY SUSPICIOUS IDENTIFICATIONS ===")
        
        suspicious_count = 0
        
        for lg in locations:
            rep = lg.representative_component
            is_suspicious = False
            reasons = []
            
            # Low confidence
            if rep.places_api_confidence and rep.places_api_confidence < 0.7:
                is_suspicious = True
                reasons.append(f"Low confidence ({rep.places_api_confidence:.2f})")
            
            # Mismatched business type and location
            location_lower = lg.location.lower()
            business_name_lower = (rep.places_api_business_name or '').lower()
            
            # Check for facility mismatches
            if any(word in location_lower for word in ['treatment', 'pumping', 'works', 'station']):
                if any(retailer in ['ASDA', 'Tesco', 'Sainsburys'] for retailer in rep.places_api_major_retailers or []):
                    is_suspicious = True
                    reasons.append("Retail business at utility facility")
            
            # Check for research centres identified as retail
            if 'research' in location_lower or 'centre' in location_lower:
                if rep.places_api_major_retailers:
                    is_suspicious = True
                    reasons.append("Retail business at research facility")
            
            # Different postcodes in name vs stored
            if 'asda' in business_name_lower and 'asda' in location_lower:
                # Extract postcodes and compare (simplified check)
                import re
                location_postcodes = re.findall(r'[A-Z]{1,2}[0-9]{1,2}[A-Z]?\\s*[0-9][A-Z]{2}', lg.location.upper())
                stored_postcode = rep.full_postcode
                if location_postcodes and stored_postcode:
                    if not any(pc.replace(' ', '') == stored_postcode.replace(' ', '') for pc in location_postcodes):
                        is_suspicious = True
                        reasons.append("Postcode mismatch")
            
            if is_suspicious:
                suspicious_count += 1
                self.stdout.write(f"\\n⚠️ LocationGroup {lg.id}:")
                self.stdout.write(f"   Location: {lg.location}")
                self.stdout.write(f"   Business: {rep.places_api_business_name}")
                self.stdout.write(f"   Strategy: {rep.places_api_search_strategy}")
                self.stdout.write(f"   Confidence: {rep.places_api_confidence}")
                self.stdout.write(f"   Reasons: {', '.join(reasons)}")
        
        self.stdout.write(f"\\n🎯 Found {suspicious_count} potentially suspicious identifications")

    def show_detailed_audit(self, locations):
        """Show detailed audit information"""
        self.stdout.write("\\n=== DETAILED AUDIT ===")
        
        for lg in locations[:20]:  # Limit to first 20 for readability
            rep = lg.representative_component
            
            self.stdout.write(f"\\n--- LocationGroup {lg.id} ---")
            self.stdout.write(f"Location: {lg.location}")
            self.stdout.write(f"Business: {rep.places_api_business_name}")
            self.stdout.write(f"Type: {rep.places_api_business_type}")
            self.stdout.write(f"Major Retailers: {rep.places_api_major_retailers}")
            self.stdout.write(f"Strategy: {rep.places_api_search_strategy}")
            self.stdout.write(f"Confidence: {rep.places_api_confidence}")
            self.stdout.write(f"Last Checked: {rep.places_api_last_checked}")
            self.stdout.write(f"Companies: {list(lg.companies.keys()) if lg.companies else []}")
            
            # Quality indicators
            quality_indicators = []
            
            if rep.places_api_confidence and rep.places_api_confidence >= 0.9:
                quality_indicators.append("High confidence")
            elif rep.places_api_confidence and rep.places_api_confidence < 0.5:
                quality_indicators.append("Low confidence")
            
            if rep.places_api_major_retailers:
                quality_indicators.append("Major retailer identified")
            
            if rep.places_api_business_type in ['energy_facility', 'water_facility']:
                quality_indicators.append("Facility type identified")
            
            if quality_indicators:
                self.stdout.write(f"Quality: {', '.join(quality_indicators)}")
        
        if locations.count() > 20:
            self.stdout.write(f"\\n... and {locations.count() - 20} more locations")
            self.stdout.write("Use --summary for overview or add filters to narrow results")