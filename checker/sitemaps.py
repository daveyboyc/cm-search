from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import LocationGroup, Component
from datetime import datetime

class StaticSitemap(Sitemap):
    priority = 1.0
    changefreq = 'weekly'
    
    def items(self):
        # Include homepage and key static pages
        return [
            'homepage',
            'capacity_market_guide', 
            'capacity_market_faq',
            'battery_storage_guide',
            'company_list_optimized',
            'technology_list',
            'search_map_view'
        ]
    
    def location(self, item):
        if item == 'homepage':
            return '/'
        elif item == 'capacity_market_guide':
            return '/guides/capacity-market/'
        elif item == 'capacity_market_faq':
            return '/guides/capacity-market-faq/'
        elif item == 'battery_storage_guide':
            return '/guides/battery-storage/'
        elif item == 'company_list_optimized':
            return '/companies/'
        elif item == 'technology_list':
            return '/technologies/'
        elif item == 'search_map_view':
            return '/search/'
        return '/'
    
    def priority(self, item):
        priorities = {
            'homepage': 1.0,
            'capacity_market_guide': 0.9,
            'capacity_market_faq': 0.95,  # High priority for FAQ targeting key search terms
            'battery_storage_guide': 0.9,
            'company_list_optimized': 0.8,
            'technology_list': 0.8,
            'search_map_view': 0.7
        }
        return priorities.get(item, 0.5)
    
    def lastmod(self, item):
        # Return current date for dynamic pages, specific dates for guides
        if item in ['capacity_market_guide', 'capacity_market_faq', 'battery_storage_guide']:
            return datetime(2025, 6, 20)  # Updated today
        return datetime.now()

class LocationSitemap(Sitemap):
    changefreq = "weekly"
    
    def items(self):
        # Only include locations with 3+ components to avoid thin content
        try:
            return LocationGroup.objects.filter(
                component_count__gte=3,
                latitude__isnull=False,
                longitude__isnull=False
            ).order_by('-component_count')[:1000]  # Limit to top 1000 locations
        except Exception as e:
            # Return empty queryset if query fails
            return LocationGroup.objects.none()
    
    def priority(self, obj):
        # Higher priority for locations with more components
        if obj.component_count >= 20:
            return 0.8
        elif obj.component_count >= 10:
            return 0.7
        elif obj.component_count >= 5:
            return 0.6
        else:
            return 0.5
    
    def lastmod(self, obj):
        try:
            return obj.updated_at
        except AttributeError:
            return None
    
    def location(self, obj):
        # Use new SEO-friendly URLs
        return f"/locations/{obj.pk}/"

class TechnologySitemap(Sitemap):
    changefreq = "monthly"
    
    def items(self):
        # Get top technologies by component count with priority weighting
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tech, component_count FROM (
                        SELECT 
                            jsonb_object_keys(technologies::jsonb) AS tech,
                            SUM(CAST(jsonb_each_text(technologies) ->> 'value' AS INTEGER)) as component_count
                        FROM checker_locationgroup 
                        WHERE technologies IS NOT NULL
                        GROUP BY tech
                        ORDER BY component_count DESC
                        LIMIT 50
                    ) tech_stats
                """)
                return [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            # Fallback to basic list if query fails
            return [
                {'name': 'Gas', 'count': 1000},
                {'name': 'Battery', 'count': 500},
                {'name': 'Wind', 'count': 400},
                {'name': 'Solar', 'count': 300},
                {'name': 'DSR', 'count': 200},
                {'name': 'Nuclear', 'count': 100},
                {'name': 'Biomass', 'count': 50},
                {'name': 'Hydro', 'count': 40},
                {'name': 'Coal', 'count': 30},
                {'name': 'Pumped Storage', 'count': 20}
            ]
    
    def location(self, item):
        from django.utils.text import slugify
        tech_name = item['name'] if isinstance(item, dict) else item
        return f"/technologies/{slugify(tech_name)}/"
    
    def priority(self, item):
        # Higher priority for technologies with more components
        if isinstance(item, dict):
            count = item.get('count', 0)
            if count >= 500:
                return 0.9
            elif count >= 200:
                return 0.8
            elif count >= 100:
                return 0.7
            elif count >= 50:
                return 0.6
            else:
                return 0.5
        return 0.7  # Default for non-dict items

class CompanySitemap(Sitemap):
    changefreq = "monthly"
    
    def items(self):
        # Get top companies by location count with priority data
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT company_name, location_count FROM (
                        SELECT 
                            jsonb_object_keys(companies::jsonb) AS company_name,
                            COUNT(*) as location_count
                        FROM checker_locationgroup 
                        WHERE companies IS NOT NULL
                        GROUP BY company_name
                        ORDER BY location_count DESC
                        LIMIT 200
                    ) company_stats
                """)
                return [{'name': row[0], 'locations': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            # Return empty list if query fails
            return []
    
    def location(self, item):
        from django.utils.text import slugify
        company_name = item['name'] if isinstance(item, dict) else item
        return f"/companies/{slugify(company_name)}/"
    
    def priority(self, item):
        # Higher priority for companies with more locations
        if isinstance(item, dict):
            locations = item.get('locations', 0)
            if locations >= 20:
                return 0.8
            elif locations >= 10:
                return 0.7
            elif locations >= 5:
                return 0.6
            else:
                return 0.5
        return 0.6  # Default for non-dict items


# Add new sitemap for content guides
class GuidesSitemap(Sitemap):
    priority = 0.9
    changefreq = 'monthly'
    
    def items(self):
        return [
            'capacity_market_guide',
            'capacity_market_faq',
            'battery_storage_guide',
            'auction_results_guide',
            'technology_overview_guide',
            'company_participation_guide'
        ]
    
    def location(self, item):
        guide_urls = {
            'capacity_market_guide': '/guides/capacity-market/',
            'capacity_market_faq': '/guides/capacity-market-faq/',
            'battery_storage_guide': '/guides/battery-storage/',
            'auction_results_guide': '/guides/auction-results/',
            'technology_overview_guide': '/guides/technology-overview/',
            'company_participation_guide': '/guides/company-participation/'
        }
        return guide_urls.get(item, '/guides/')
    
    def lastmod(self, item):
        # Current guides have been updated
        if item in ['capacity_market_guide', 'capacity_market_faq', 'battery_storage_guide']:
            return datetime(2025, 6, 20)
        # Future guides will be added
        return datetime(2025, 6, 20)
    
    def priority(self, item):
        priorities = {
            'capacity_market_guide': 0.95,
            'capacity_market_faq': 0.93,
            'battery_storage_guide': 0.9,
            'auction_results_guide': 0.85,
            'technology_overview_guide': 0.8,
            'company_participation_guide': 0.75
        }
        return priorities.get(item, 0.7)