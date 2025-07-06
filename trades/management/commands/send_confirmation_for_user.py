from django.core.management.base import BaseCommand
from trades.models import TradingAdvert
from trades.views import send_confirmation_email


class Command(BaseCommand):
    help = 'Send confirmation email for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to send confirmation to')

    def handle(self, *args, **options):
        email = options['email']
        
        # Find the advert for this email
        advert = TradingAdvert.objects.filter(contact_email=email).first()
        
        if advert:
            self.stdout.write(f'Found advert ID {advert.id} for {advert.contact_email}')
            self.stdout.write(f'Type: {advert.type_display}, Capacity: {advert.capacity_display}')
            self.stdout.write(f'Paid: {advert.is_paid}, Active: {advert.is_active}')
            
            try:
                # Send the confirmation email
                send_confirmation_email(advert)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Confirmation email sent to {email}!')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to send email: {e}')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'No advert found for {email}')
            )