from django.core.management.base import BaseCommand
from trades.models import TradingAdvert

class Command(BaseCommand):
    help = 'Update contact emails for testing'

    def handle(self, *args, **options):
        # Update all adverts to use your email for testing
        updated = TradingAdvert.objects.filter(is_active=True).update(
            contact_email='davidcrawford83@gmail.com'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated} adverts with test email: davidcrawford83@gmail.com')
        )