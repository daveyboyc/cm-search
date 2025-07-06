from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from trades.models import TradingAdvert
from datetime import datetime, timedelta
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Creates dummy trading adverts for testing'

    def handle(self, *args, **options):
        # Get or create test users
        test_users = []
        for i in range(5):
            user, created = User.objects.get_or_create(
                username=f'trader{i+1}',
                defaults={
                    'email': f'trader{i+1}@example.com',
                    'first_name': f'Test',
                    'last_name': f'Trader{i+1}'
                }
            )
            test_users.append(user)
        
        # Sample data for realistic adverts
        selling_descriptions = [
            "T-4 2018/19 auction capacity available. Located in South East England. Flexible on volume for the right price. Can split capacity if needed.",
            "Excess battery storage capacity from T-1 2023/24. Technology agnostic buyer preferred. Will consider 80-120MW deals.",
            "Gas CCGT capacity available. Original auction price £22.50/kW/yr. Open to negotiation. Can provide up to 150MW if required.",
            "DSR capacity from industrial site. Very reliable, 99% availability. Minimum 10MW, maximum 50MW available.",
            "Wind + battery hybrid site capacity. Selling due to site closure. Quick sale needed. Volume negotiable 40-60MW.",
            "Surplus capacity from T-4 2019/20. Mix of technologies available. Prefer single buyer but will split.",
            "Interconnector capacity rights. Belgium border. Fixed 75MW but timing flexible within delivery year.",
            "Nuclear capacity available due to contract changes. Premium reliability. 100MW minimum, up to 200MW available.",
            "Pumped storage capacity. Wales location. 25-35MW range acceptable. Includes performance bonus rights.",
            "Coal plant capacity (pre-closure). Must transfer before October. Any reasonable offer considered. 50-100MW."
        ]
        
        buying_descriptions = [
            "Need 50-75MW for compliance. Technology agnostic but prefer low carbon. South England preferred.",
            "Seeking 100MW+ capacity urgent. Battery or DSR preferred. Can work with 80-120MW range. Price negotiable.",
            "Looking for reliable baseload capacity. Gas or nuclear preferred. Need 150-200MW. Premium for proven availability.",
            "Want to buy 20-30MW DSR or battery capacity. London area ideal. Flexible on exact volume.",
            "Aggregator seeking multiple small capacities. Will buy 5-50MW parcels. Any technology considered.",
            "Industrial user needs backup capacity. 40-60MW range. Prefer same grid zone. Technology flexible.",
            "New supplier seeking first capacity purchase. 25-40MW ideal. Will pay premium for simple transfer.",
            "Expanding portfolio - need 200MW+ total. Will consider multiple sellers. 50MW minimum parcels.",
            "Urgent: Failed unit replacement needed. 75-100MW required. Any technology. Quick completion bonus available.",
            "Building balanced portfolio. Seeking mix of technologies. 30-150MW parcels. Prefer diverse locations."
        ]
        
        # Create selling adverts
        for i in range(15):
            base_mw = random.choice([10, 20, 25, 30, 40, 50, 75, 100, 150, 200])
            advert = TradingAdvert.objects.create(
                user=random.choice(test_users),
                is_offer=True,
                capacity_mw=base_mw,
                delivery_year=random.choice([2025, 2026, 2027, 2028]),
                price_gbp_per_kw_yr=random.choice([15.50, 18.00, 20.00, 22.50, 25.00, None]),  # Some POA
                description=random.choice(selling_descriptions),
                contact_email=f"trading{random.randint(1,5)}@energyco.com",
                is_paid=True,
                is_active=True,
                expires_at=timezone.now() + timedelta(days=random.randint(10, 30))
            )
            self.stdout.write(f"Created selling advert: {advert}")
        
        # Create buying adverts
        for i in range(10):
            base_mw = random.choice([20, 30, 50, 75, 100, 150])
            advert = TradingAdvert.objects.create(
                user=random.choice(test_users),
                is_offer=False,
                capacity_mw=base_mw,
                delivery_year=random.choice([2025, 2026, 2027]),
                price_gbp_per_kw_yr=random.choice([16.00, 19.00, 21.00, None]),  # Buyers often don't state price
                description=random.choice(buying_descriptions),
                contact_email=f"procurement{random.randint(1,5)}@utilityco.com",
                is_paid=True,
                is_active=True,
                expires_at=timezone.now() + timedelta(days=random.randint(15, 30))
            )
            self.stdout.write(f"Created buying advert: {advert}")
        
        self.stdout.write(self.style.SUCCESS('Successfully created 25 dummy adverts'))