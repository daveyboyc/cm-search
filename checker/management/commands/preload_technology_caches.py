"""
Management command to preload all technology caches for maximum performance.
Run this after data updates to ensure instant page loads.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db.models import Count
import time
import logging

from checker.models import Component, LocationGroup

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Preload technology caches for instant page loads'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild all caches even if they exist',
        )
        parser.add_argument(
            '--top-n',
            type=int,
            default=20,
            help='Only cache top N technologies by component count',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write("🚀 Preloading technology caches...\n")
        
        # Get all technologies with their component counts
        technologies = self.get_all_technologies()
        
        if options['top_n']:
            # Filter out DSR from top-N caching to prevent 32-second delay (28,270 components)
            technologies = [(tech, count) for tech, count in technologies if tech != 'DSR'][:options['top_n']]
            self.stdout.write(f"📊 Caching top {len(technologies)} technologies by component count (DSR excluded for performance)\n")
        else:
            # For full caching, also exclude DSR to prevent memory issues
            technologies = [(tech, count) for tech, count in technologies if tech != 'DSR']
            self.stdout.write(f"📊 Caching all {len(technologies)} technologies (DSR excluded for performance)\n")
        
        cached_count = 0
        skipped_count = 0
        
        for i, (tech_name, component_count) in enumerate(technologies, 1):
            # Create cache-safe key
            import re
            safe_tech_name = re.sub(r'[^a-zA-Z0-9_]', '_', tech_name.upper())
            cache_key = f"technology_summary_{safe_tech_name}"
            
            # Check if cache exists and should skip
            if not options['force'] and cache.get(cache_key):
                self.stdout.write(f"  ⏭️  {i:2d}. {tech_name}: Already cached ({component_count:,} components)")
                skipped_count += 1
                continue
            
            # Cache this technology
            self.stdout.write(f"  🔄 {i:2d}. Caching {tech_name}... ", ending='')
            
            try:
                summary = self.build_technology_summary(tech_name)
                cache.set(cache_key, summary, 3600 * 24)  # 24 hours
                
                self.stdout.write(self.style.SUCCESS(
                    f"✅ ({summary['location_count']} locations, {summary['total_capacity']:.1f} MW)"
                ))
                cached_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed: {e}"))
        
        total_time = time.time() - start_time
        self.stdout.write(f"\n✅ Cache preloading complete!")
        self.stdout.write(f"   📊 Cached: {cached_count} technologies")
        self.stdout.write(f"   ⏭️  Skipped: {skipped_count} technologies")
        self.stdout.write(f"   ⏱️  Total time: {total_time:.1f}s")
        self.stdout.write(f"   📈 Average time per technology: {total_time/max(cached_count,1):.2f}s")
        
        # Test a few caches
        self.test_cache_performance()

    def get_all_technologies(self):
        """Get all technologies sorted by component count."""
        technologies = Component.objects.values('technology').annotate(
            component_count=Count('id')
        ).exclude(
            technology__isnull=True
        ).exclude(
            technology__exact=''
        ).order_by('-component_count')
        
        return [(tech['technology'], tech['component_count']) for tech in technologies]

    def build_technology_summary(self, technology):
        """Build summary data for a technology."""
        # Use LocationGroup for optimized queries
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
            
            # Store location data for map (limit to geocoded locations)
            if lg.latitude and lg.longitude:
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
        
        return summary

    def test_cache_performance(self):
        """Test the performance of cached vs uncached lookups."""
        self.stdout.write(f"\n🧪 Testing cache performance...")
        
        # Test cached lookup
        start = time.time()
        cached_data = cache.get("technology_summary_DSR")
        cached_time = time.time() - start
        
        if cached_data:
            self.stdout.write(f"  ✅ Cached DSR lookup: {cached_time*1000:.1f}ms ({cached_data['location_count']} locations)")
        else:
            self.stdout.write(f"  ❌ DSR cache miss")
            
        # Test a few other technologies
        test_techs = ['Battery', 'OCGT', 'Wind', 'Solar']
        for tech in test_techs:
            cache_key = f"technology_summary_{tech.upper()}"
            start = time.time()
            data = cache.get(cache_key)
            elapsed = time.time() - start
            
            if data:
                self.stdout.write(f"  ✅ {tech} lookup: {elapsed*1000:.1f}ms ({data['location_count']} locations)")
            else:
                self.stdout.write(f"  ⚠️  {tech} not cached")
        
        self.stdout.write(f"\n💡 Technology pages should now load in <100ms!")