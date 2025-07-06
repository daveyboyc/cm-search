from django.core.management.base import BaseCommand
from django.conf import settings
import stripe

class Command(BaseCommand):
    help = 'Create Stripe product and price for £5 trading advert fee'

    def handle(self, *args, **options):
        # Set up Stripe API key
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        try:
            # Create product for trading adverts
            product = stripe.Product.create(
                name='Trading Board Advert',
                description='Post capacity market trading advert for 30 days',
                type='service'
            )
            
            self.stdout.write(f'✅ Created product: {product.id}')
            
            # Create price for £5 one-time payment
            price = stripe.Price.create(
                unit_amount=500,  # £5.00 in pence
                currency='gbp',
                product=product.id,
                nickname='Trading Advert Fee'
            )
            
            self.stdout.write(f'✅ Created price: {price.id}')
            self.stdout.write(f'💰 Amount: £{price.unit_amount/100:.2f}')
            
            self.stdout.write(f'\n📋 Add this to your environment variables:')
            self.stdout.write(f'STRIPE_TRADING_ADVERT_PRICE_ID={price.id}')
            
            self.stdout.write(f'\n🔧 Or update settings.py:')
            self.stdout.write(f"STRIPE_TRADING_ADVERT_PRICE_ID = os.environ.get('STRIPE_TRADING_ADVERT_PRICE_ID', '{price.id}')")
            
        except stripe.error.StripeError as e:
            self.stdout.write(self.style.ERROR(f'❌ Stripe error: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))