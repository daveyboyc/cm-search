from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create test users for access control testing'

    def handle(self, *args, **options):
        # Create multiple test users (no premium access)
        test_users = [
            ('testuser', 'testuser@example.com'),
            ('testuser2', 'testuser2@example.com'),
            ('testuser3', 'testuser3@example.com'),
        ]
        password = 'testpass123'
        
        # Create multiple test users
        for username, email in test_users:
            # Delete existing test user if exists
            User.objects.filter(username=username).delete()
            
            # Create new test user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create UserProfile with no paid access
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'has_paid_access': False,
                    'payment_intent_id': None,
                    'free_access_start_time': timezone.now(),
                    'stripe_payment_status': 'none'
                }
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ Created test user:\n'
                f'   Username: {username}\n'
                f'   Password: {password}\n'
                f'   Email: {email}\n'
                f'   Has Premium: No\n'
            ))
        
        # Also create a premium test user for comparison
        premium_username = 'premiumuser'
        premium_email = 'premiumuser@example.com'
        
        # Delete existing premium test user if exists
        User.objects.filter(username=premium_username).delete()
        
        # Create premium test user
        premium_user = User.objects.create_user(
            username=premium_username,
            email=premium_email,
            password=password
        )
        
        # Create UserProfile with paid access
        premium_profile, created = UserProfile.objects.get_or_create(
            user=premium_user,
            defaults={
                'has_paid_access': True,
                'payment_intent_id': 'test_payment_intent',
                'free_access_start_time': timezone.now(),
                'stripe_payment_status': 'succeeded'
            }
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Created premium test user:\n'
            f'   Username: {premium_username}\n'
            f'   Password: {password}\n'
            f'   Email: {premium_email}\n'
            f'   Has Premium: Yes'
        ))
        
        self.stdout.write(self.style.SUCCESS(
            '\n🔑 You can now test access control with these accounts!'
        ))