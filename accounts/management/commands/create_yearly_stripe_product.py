from django.core.management.base import BaseCommand
from django.conf import settings
import stripe

class Command(BaseCommand):
    help = 'Create Stripe product and price for £5/year subscription'

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        try:
            # Create product for yearly access
            product = stripe.Product.create(
                name='Capacity Market Search - Full Access (Annual)',
                description='Unlimited access to all features for one year. Includes searches, maps, analytics, and all future features.',
                type='service',
                metadata={
                    'access_level': 'full',
                    'duration': 'yearly'
                }
            )
            
            self.stdout.write(f"✅ Created product: {product.id}")
            self.stdout.write(f"   Name: {product.name}")
            
            # Create price for £5/year (recurring annually)
            price = stripe.Price.create(
                product=product.id,
                unit_amount=500,  # £5.00 in pence
                currency='gbp',
                recurring={'interval': 'year'},  # Annual subscription
                metadata={
                    'access_level': 'full',
                    'duration': 'yearly'
                }
            )
            
            self.stdout.write(f"✅ Created yearly price: {price.id}")
            self.stdout.write(f"   Amount: £{price.unit_amount / 100}/year")
            self.stdout.write(f"   Interval: {price.recurring['interval']}")
            
            self.stdout.write(self.style.SUCCESS(f"\n🎉 Stripe setup complete!"))
            self.stdout.write(f"📋 Add this to your environment variables:")
            self.stdout.write(f"   STRIPE_YEARLY_ACCESS_PRICE_ID={price.id}")
            
            # Also list existing products for reference
            self.stdout.write(f"\n📊 All products:")
            products = stripe.Product.list(limit=10)
            for prod in products.data:
                self.stdout.write(f"   {prod.id}: {prod.name}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating Stripe product: {str(e)}')
            )