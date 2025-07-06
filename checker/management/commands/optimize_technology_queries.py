"""
Management command to optimize technology-related queries in views.
"""
from django.core.management.base import BaseCommand
from django.db import connection
import time
import json
from checker.models import Component, LocationGroup

class Command(BaseCommand):
    help = 'Optimize technology queries and create cached data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--technology',
            type=str,
            help='Specific technology to optimize (e.g., DSR)',
        )
        parser.add_argument(
            '--cache-all',
            action='store_true',
            help='Cache all technology data',
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Optimizing technology queries...\n")
        
        # Create indexes first
        self.create_indexes()
        
        # Cache technology data
        if options['cache_all']:
            self.cache_all_technologies()
        elif options['technology']:
            self.cache_technology(options['technology'])
        
        # Show optimization tips
        self.show_optimization_tips()

    def create_indexes(self):
        """Create necessary indexes for performance."""
        self.stdout.write("\n📊 Creating database indexes...")
        
        with connection.cursor() as cursor:
            indexes = [
                # Functional indexes for case-insensitive searches
                ("idx_component_technology_upper", 
                 "CREATE INDEX IF NOT EXISTS idx_component_technology_upper ON checker_component (UPPER(technology))"),
                
                # Composite indexes for common query patterns
                ("idx_component_tech_year", 
                 "CREATE INDEX IF NOT EXISTS idx_component_tech_year ON checker_component (UPPER(technology), delivery_year DESC)"),
                
                ("idx_component_tech_location", 
                 "CREATE INDEX IF NOT EXISTS idx_component_tech_location ON checker_component (UPPER(technology), location)"),
                
                # LocationGroup indexes
                ("idx_locationgroup_location", 
                 "CREATE INDEX IF NOT EXISTS idx_locationgroup_location ON checker_locationgroup (location)"),
                
                # Partial index for geocoded components
                ("idx_component_geocoded_tech", 
                 "CREATE INDEX IF NOT EXISTS idx_component_geocoded_tech ON checker_component (UPPER(technology)) WHERE geocoded = true"),
            ]
            
            for index_name, index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(self.style.SUCCESS(f"✅ Created {index_name}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️  {index_name}: {e}"))

    def cache_technology(self, technology):
        """Cache data for a specific technology."""
        from django.core.cache import cache
        
        self.stdout.write(f"\n🔧 Caching data for {technology}...")
        
        # Use LocationGroup for optimized queries
        start_time = time.time()
        
        # Get all LocationGroups with this technology
        location_groups = LocationGroup.objects.filter(
            technologies__icontains=technology
        ).select_related()
        
        # Build summary data
        summary = {
            'technology': technology,
            'location_count': location_groups.count(),
            'total_capacity': 0,
            'companies': set(),
            'years': set(),
            'locations': []
        }
        
        for lg in location_groups:
            # Aggregate data from the LocationGroup
            if lg.normalized_capacity_mw:
                summary['total_capacity'] += float(lg.normalized_capacity_mw)
            
            if lg.companies:
                summary['companies'].update(lg.companies)
            
            if lg.auction_years:
                summary['years'].update(lg.auction_years)
            
            # Store location data for map
            summary['locations'].append({
                'location': lg.location,
                'lat': lg.latitude,
                'lng': lg.longitude,
                'capacity': lg.normalized_capacity_mw,
                'component_count': lg.component_count
            })
        
        # Convert sets to lists for JSON serialization
        summary['companies'] = sorted(list(summary['companies']))
        summary['years'] = sorted(list(summary['years']), reverse=True)
        
        # Cache the summary
        cache_key = f"technology_summary_{technology.upper()}"
        cache.set(cache_key, summary, 3600 * 24)  # 24 hours
        
        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"✅ Cached {technology}: {summary['location_count']} locations in {elapsed:.2f}s"
        ))

    def cache_all_technologies(self):
        """Cache data for all technologies."""
        self.stdout.write("\n📦 Caching all technology data...")
        
        # Get unique technologies
        technologies = Component.objects.values_list(
            'technology', flat=True
        ).distinct().exclude(technology__isnull=True)
        
        for tech in technologies:
            if tech:  # Skip empty values
                self.cache_technology(tech)

    def show_optimization_tips(self):
        """Show code optimization tips."""
        self.stdout.write("\n💡 View Optimization Tips:")
        self.stdout.write("""
Update your views with these optimizations:

1. In views_technology_optimized.py, replace:
   ❌ components = Component.objects.filter(technology__icontains=technology)
   
   With:
   ✅ location_groups = LocationGroup.objects.filter(
       technologies__contains=[technology]
   ).select_related()

2. For case-insensitive matching:
   ✅ LocationGroup.objects.filter(
       technologies__icontains=technology
   )

3. Use cached summaries:
   from django.core.cache import cache
   summary = cache.get(f"technology_summary_{technology.upper()}")
   if summary:
       # Use cached data
       pass

4. For map data, use the optimized LocationGroup model:
   ✅ LocationGroup.objects.filter(
       technologies__contains=[technology],
       latitude__isnull=False,
       longitude__isnull=False
   ).values('location', 'latitude', 'longitude', 'capacity_mw')
""")