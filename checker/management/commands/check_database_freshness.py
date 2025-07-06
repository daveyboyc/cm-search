from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from checker.models import Component
import requests
import hashlib
import time

class Command(BaseCommand):
    help = 'Check if database is up-to-date with NESO APIs without full crawl'

    def add_arguments(self, parser):
        parser.add_argument(
            '--method',
            type=str,
            choices=['count', 'hash', 'auction', 'all'],
            default='all',
            help='Method to use for freshness check'
        )

    def handle(self, *args, **options):
        method = options['method']
        
        self.stdout.write("🔍 Checking database freshness against NESO APIs...")
        
        if method in ['count', 'all']:
            self.check_counts()
        
        if method in ['hash', 'all']:
            self.check_hash()
            
        if method in ['auction', 'all']:
            self.check_latest_auction()

    def check_counts(self):
        """Compare total counts between API and database"""
        self.stdout.write("\n📊 COUNT-BASED CHECK")
        
        try:
            # Get database counts
            db_component_count = Component.objects.count()
            db_cmu_count = Component.objects.values('cmu_id').distinct().count()
            
            self.stdout.write(f"Database components: {db_component_count}")
            self.stdout.write(f"Database unique CMUs: {db_cmu_count}")
            
            # Get API counts
            self.stdout.write("Fetching counts from NESO API...")
            api_component_count = self.fetch_component_count_from_api()
            api_cmu_count = self.fetch_cmu_count_from_api()
            
            if api_component_count is not None:
                self.stdout.write(f"API components: {api_component_count}")
                component_diff = api_component_count - db_component_count
                if component_diff == 0:
                    self.stdout.write(self.style.SUCCESS("✅ Component count matches"))
                elif component_diff > 0:
                    self.stdout.write(self.style.WARNING(f"⚠️  Database missing {component_diff} components"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  Database has {abs(component_diff)} extra components"))
            
            if api_cmu_count is not None:
                self.stdout.write(f"API unique CMUs: {api_cmu_count}")
                cmu_diff = api_cmu_count - db_cmu_count
                if cmu_diff == 0:
                    self.stdout.write(self.style.SUCCESS("✅ CMU count matches"))
                elif cmu_diff > 0:
                    self.stdout.write(self.style.WARNING(f"⚠️  Database missing {cmu_diff} CMUs"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  Database has {abs(cmu_diff)} extra CMUs"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Count check failed: {e}"))

    def check_hash(self):
        """Compare hash of recent records"""
        self.stdout.write("\n🔒 HASH-BASED CHECK")
        
        try:
            # Get sample from database
            db_sample = list(Component.objects.order_by('-id')[:100].values_list('cmu_id', flat=True))
            db_hash = hashlib.md5(''.join(sorted(db_sample)).encode()).hexdigest()
            
            self.stdout.write(f"Database hash (last 100 CMUs): {db_hash[:12]}...")
            
            # TODO: Fetch same sample from API
            self.stdout.write("⚠️  Need to implement API hash comparison")
            self.stdout.write("   Add: fetch_latest_cmu_ids_from_api()")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Hash check failed: {e}"))

    def check_latest_auction(self):
        """Check if we have the latest auction data"""
        self.stdout.write("\n📅 AUCTION-BASED CHECK")
        
        try:
            # Get latest auction from database
            latest_db_auction = Component.objects.aggregate(
                latest=Max('auction_name')
            )['latest']
            
            latest_db_year = Component.objects.aggregate(
                latest=Max('delivery_year')
            )['latest']
            
            self.stdout.write(f"Latest database auction: {latest_db_auction}")
            self.stdout.write(f"Latest database year: {latest_db_year}")
            
            # Check component creation dates
            from django.utils import timezone
            from datetime import timedelta
            
            week_ago = timezone.now() - timedelta(days=7)
            recent_components = Component.objects.filter(created_at__gte=week_ago).count()
            
            self.stdout.write(f"Components added in last 7 days: {recent_components}")
            
            if recent_components == 0:
                self.stdout.write(self.style.WARNING("⚠️  No recent components - might need crawl"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Recent activity detected"))
                
            # Compare with API
            self.stdout.write("Fetching latest auction from NESO API...")
            api_latest_year = self.get_latest_auction_from_api()
            
            if api_latest_year:
                self.stdout.write(f"API latest delivery year: {api_latest_year}")
                if latest_db_year == api_latest_year:
                    self.stdout.write(self.style.SUCCESS("✅ Latest delivery year matches"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  Database latest: {latest_db_year}, API latest: {api_latest_year}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Auction check failed: {e}"))

    def fetch_component_count_from_api(self):
        """Fetch total component count from NESO API"""
        try:
            component_api_url = "https://api.neso.energy/api/3/action/datastore_search"
            component_resource_id = "790f5fa0-f8eb-4d82-b98d-0d34d3e404e8"
            
            params = {
                "resource_id": component_resource_id,
                "limit": 0  # Get count only
            }
            
            response = requests.get(component_api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data.get("result", {}).get("total", 0)
            return 0
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API component count failed: {e}"))
            return None

    def fetch_cmu_count_from_api(self):
        """Fetch unique CMU count from NESO API"""
        try:
            cmu_api_url = "https://api.neso.energy/api/3/action/datastore_search"
            cmu_resource_id = "25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6"
            
            params = {
                "resource_id": cmu_resource_id,
                "limit": 0  # Get count only
            }
            
            response = requests.get(cmu_api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data.get("result", {}).get("total", 0)
            return 0
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API CMU count failed: {e}"))
            return None

    def get_latest_auction_from_api(self):
        """Get the latest auction name from NESO API"""
        try:
            # Get latest CMU records to find newest auction
            cmu_api_url = "https://api.neso.energy/api/3/action/datastore_search"
            cmu_resource_id = "25a5fa2e-873d-41c5-8aaf-fbc2b06d79e6"
            
            params = {
                "resource_id": cmu_resource_id,
                "limit": 50,  # Get recent records
                "sort": "_id desc"  # Sort by newest first
            }
            
            response = requests.get(cmu_api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                records = data.get("result", {}).get("records", [])
                if records:
                    # Look for delivery year or auction name in recent records
                    latest_year = None
                    for record in records:
                        delivery_year = record.get("Delivery Year")
                        if delivery_year and (not latest_year or delivery_year > latest_year):
                            latest_year = delivery_year
                    return latest_year
            return None
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API latest auction failed: {e}"))
            return None