from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db.models import Count, Sum, Q
from checker.models import Component
import json
import time


class Command(BaseCommand):
    help = 'Build and cache statistics data to speed up the statistics page'

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write('Building statistics cache...')
        
        stats_data = {}
        
        # 1. Summary Statistics
        self.stdout.write('Calculating summary stats...')
        stats_data['summary'] = {
            'total_components': Component.objects.count(),
            'total_companies': Component.objects.exclude(
                Q(company_name__isnull=True) | Q(company_name='')
            ).values('company_name').distinct().count(),
            'total_technologies': Component.objects.values('technology').distinct().count(),
            'total_capacity': float(
                Component.objects.aggregate(
                    total=Sum('derated_capacity_mw')
                )['total'] or 0
            )
        }
        
        # 2. Top Companies by Component Count
        self.stdout.write('Calculating top companies by count...')
        top_companies_count = list(
            Component.objects.exclude(Q(company_name__isnull=True) | Q(company_name=''))
            .values('company_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:25]
        )
        stats_data['top_companies_count'] = top_companies_count
        
        # 3. Top Companies by Capacity
        self.stdout.write('Calculating top companies by capacity...')
        top_companies_capacity = list(
            Component.objects.exclude(Q(company_name__isnull=True) | Q(company_name=''))
            .filter(derated_capacity_mw__isnull=False)
            .values('company_name')
            .annotate(total_capacity=Sum('derated_capacity_mw'))
            .filter(total_capacity__gt=0)
            .order_by('-total_capacity')[:25]
        )
        # Convert Decimal to float for JSON serialization
        for company in top_companies_capacity:
            company['total_capacity'] = float(company['total_capacity'])
        stats_data['top_companies_capacity'] = top_companies_capacity
        
        # 4. Technologies by Count
        self.stdout.write('Calculating technologies by count...')
        tech_by_count = list(
            Component.objects.exclude(Q(technology__isnull=True) | Q(technology=''))
            .values('technology')
            .annotate(count=Count('id'))
            .order_by('-count')[:25]
        )
        stats_data['tech_by_count'] = tech_by_count
        
        # 5. Technologies by Capacity
        self.stdout.write('Calculating technologies by capacity...')
        tech_by_capacity = list(
            Component.objects.exclude(Q(technology__isnull=True) | Q(technology=''))
            .filter(derated_capacity_mw__isnull=False)
            .values('technology')
            .annotate(total_capacity=Sum('derated_capacity_mw'))
            .filter(total_capacity__gt=0)
            .order_by('-total_capacity')[:25]
        )
        for tech in tech_by_capacity:
            tech['total_capacity'] = float(tech['total_capacity'])
        stats_data['tech_by_capacity'] = tech_by_capacity
        
        # 6. Components by Year
        self.stdout.write('Calculating components by year...')
        components_by_year = list(
            Component.objects.exclude(Q(delivery_year__isnull=True) | Q(delivery_year=''))
            .values('delivery_year')
            .annotate(count=Count('id'))
            .order_by('delivery_year')
        )
        stats_data['components_by_year'] = components_by_year
        
        # 7. Top Components by Capacity
        self.stdout.write('Calculating top components by capacity...')
        top_components_capacity = list(
            Component.objects.filter(derated_capacity_mw__isnull=False)
            .filter(derated_capacity_mw__gt=0)
            .order_by('-derated_capacity_mw')[:20]
            .values('id', 'location', 'company_name', 'technology', 'derated_capacity_mw')
        )
        for comp in top_components_capacity:
            comp['derated_capacity_mw'] = float(comp['derated_capacity_mw'])
        stats_data['top_components_capacity'] = top_components_capacity
        
        # Cache the data for 6 hours
        cache_key = 'statistics_page_data'
        cache.set(cache_key, json.dumps(stats_data), timeout=60*60*6)
        
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully cached statistics data in {elapsed:.2f}s'
            )
        )
        self.stdout.write(f'Cache key: {cache_key}')
        self.stdout.write(f'Cache expiry: 6 hours')