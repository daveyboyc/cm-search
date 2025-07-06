import stripe
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Create Stripe products for tiered pricing (£2 List Access, £5 Full Access)'

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        try:
            # Create £2 List Access product
            list_access_product = stripe.Product.create(
                name='Capacity Market Search - List Access',
                description='Unlimited searches and list views (no map access)',
                metadata={
                    'access_level': 'list_only',
                    'features': 'unlimited_searches,list_views,export_data'
                }
            )
            
            list_access_price = stripe.Price.create(
                product=list_access_product.id,
                unit_amount=200,  # £2.00 in pence
                currency='gbp',
                metadata={
                    'access_level': 'list_only'
                }
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created £2 List Access product:\n'
                    f'   Product ID: {list_access_product.id}\n'
                    f'   Price ID: {list_access_price.id}'
                )
            )
            
            # Create £5 Full Access product
            full_access_product = stripe.Product.create(
                name='Capacity Market Search - Full Access',
                description='Unlimited access to all features including interactive maps',
                metadata={
                    'access_level': 'full',
                    'features': 'unlimited_searches,list_views,map_access,export_data,analytics'
                }
            )
            
            full_access_price = stripe.Price.create(
                product=full_access_product.id,
                unit_amount=500,  # £5.00 in pence
                currency='gbp',
                metadata={
                    'access_level': 'full'
                }
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created £5 Full Access product:\n'
                    f'   Product ID: {full_access_product.id}\n'
                    f'   Price ID: {full_access_price.id}'
                )
            )
            
            # Output configuration for settings
            self.stdout.write(
                self.style.WARNING(
                    f'\n📝 Add these to your settings.py or environment variables:\n\n'
                    f'# Stripe Price IDs\n'
                    f'STRIPE_LIST_ACCESS_PRICE_ID = "{list_access_price.id}"\n'
                    f'STRIPE_FULL_ACCESS_PRICE_ID = "{full_access_price.id}"\n\n'
                    f'# Stripe Product IDs\n'
                    f'STRIPE_LIST_ACCESS_PRODUCT_ID = "{list_access_product.id}"\n'
                    f'STRIPE_FULL_ACCESS_PRODUCT_ID = "{full_access_product.id}"\n'
                )
            )
            
        except stripe.error.StripeError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Stripe API error: {str(e)}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Unexpected error: {str(e)}')
            )