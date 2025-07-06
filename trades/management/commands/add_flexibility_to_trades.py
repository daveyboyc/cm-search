from django.core.management.base import BaseCommand
from trades.models import TradingAdvert
import random


class Command(BaseCommand):
    help = 'Adds flexibility flags to existing trading adverts for testing'

    def handle(self, *args, **options):
        adverts = TradingAdvert.objects.all()
        updated = 0
        
        for advert in adverts:
            # Randomly add flexibility flags to make it realistic
            if random.random() < 0.3:  # 30% chance
                advert.capacity_flexible = True
            
            if random.random() < 0.4:  # 40% chance
                advert.price_estimate = True
                
            advert.save()
            updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated} adverts with flexibility flags')
        )