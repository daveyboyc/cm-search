from django.core.management.base import BaseCommand
from django.utils import timezone
from trades.models import TradingAdvert


class Command(BaseCommand):
    help = 'Expire adverts that have passed their expiry date'

    def handle(self, *args, **options):
        # Find adverts that have expired
        expired_adverts = TradingAdvert.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        )
        
        count = expired_adverts.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No adverts to expire"))
            return
        
        self.stdout.write(f"Found {count} expired adverts")
        
        # Deactivate expired adverts
        updated = expired_adverts.update(is_active=False)
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Successfully expired {updated} adverts")
        )
        
        # Log which adverts were expired
        for advert in expired_adverts:
            self.stdout.write(
                f"  - #{advert.pk}: {advert.type_display} {advert.capacity_display} "
                f"(expired {advert.expires_at})"
            )