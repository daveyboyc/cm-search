from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from trades.models import TradingAdvert
from datetime import datetime
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create test adverts specifically for testing messaging system'

    def handle(self, *args, **options):
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Clear existing test adverts
        TradingAdvert.objects.filter(description__icontains='TEST MESSAGE').delete()
        
        test_adverts = [
            {
                'is_offer': True,
                'capacity_mw': 50.0,
                'delivery_year': 2025,
                'price_gbp_per_kw_yr': 45.00,
                'description': 'TEST MESSAGE ADVERT 1: PUBLIC EMAIL - Battery storage facility available for secondary trading. Well maintained and reliable.',
                'contact_email': 'davidcrawford83@gmail.com',
                'show_email_publicly': True,  # PUBLIC EMAIL
                'capacity_flexible': False,
                'price_estimate': False,
            },
            {
                'is_offer': False,
                'capacity_mw': 25.0,
                'delivery_year': 2025,
                'price_gbp_per_kw_yr': 50.00,
                'description': 'TEST MESSAGE ADVERT 2: PRIVATE MESSAGING - Looking to purchase capacity obligations. Flexible on terms and location.',
                'contact_email': 'davidcrawford83@gmail.com',
                'show_email_publicly': False,  # PRIVATE MESSAGING
                'capacity_flexible': True,
                'price_estimate': True,
            },
            {
                'is_offer': True,
                'capacity_mw': 100.0,
                'delivery_year': 2026,
                'price_gbp_per_kw_yr': None,  # POA
                'description': 'TEST MESSAGE ADVERT 3: PRIVATE MESSAGING - Large gas peaker plant capacity available. Price on application.',
                'contact_email': 'davidcrawford83@gmail.com',
                'show_email_publicly': False,  # PRIVATE MESSAGING
                'capacity_flexible': False,
                'price_estimate': False,
            }
        ]
        
        created_count = 0
        for advert_data in test_adverts:
            advert_data['user'] = user
            advert_data['is_paid'] = True
            advert_data['expires_at'] = timezone.now() + timezone.timedelta(days=30)
            
            advert = TradingAdvert.objects.create(**advert_data)
            created_count += 1
            
            privacy_type = "PUBLIC EMAIL" if advert.show_email_publicly else "PRIVATE MESSAGING"
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created #{advert.pk}: {advert.type_display} {advert.capacity_mw}MW '
                    f'({privacy_type}) - {advert.description[:50]}...'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 Created {created_count} test adverts for messaging system testing')
        )
        self.stdout.write(
            self.style.WARNING('\n📋 Testing Instructions:')
        )
        self.stdout.write('1. Go to http://localhost:8000/trades/')
        self.stdout.write('2. Look for "TEST MESSAGE ADVERT" entries')
        self.stdout.write('3. Test PUBLIC EMAIL advert - should show email directly')
        self.stdout.write('4. Test PRIVATE MESSAGING adverts - should show "Send Message" button')
        self.stdout.write('5. Send messages and check console output for email content')
        self.stdout.write('6. Verify success/error messages appear correctly')