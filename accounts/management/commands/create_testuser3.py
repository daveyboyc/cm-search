#!/usr/bin/env python
"""
Django management command to create testuser3 as a £2 paid user
Usage: python manage.py create_testuser3
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create testuser3 as a £2 paid user (list_only access level)'

    def handle(self, *args, **options):
        username = 'testuser3'
        email = 'testuser3@example.com'
        password = 'password123'
        
        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                self.stdout.write(
                    self.style.WARNING(f'User {username} already exists - updating profile...')
                )
            else:
                # Create the user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created user: {username}')
                )
            
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Set as paid user with £2 payment
            profile.has_paid_access = True
            profile.payment_amount = 2.00
            profile.free_access_start_time = None  # Not needed for paid users
            profile.save()
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created profile for {username}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Updated profile for {username}')
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'''
🎯 testuser3 Setup Complete:
   Username: {username}
   Password: {password}
   Email: {email}
   Access Level: list_only (£2 paid)
   Payment Amount: £{profile.payment_amount}
   Has Paid Access: {profile.has_paid_access}
   
📝 Testing Notes:
   - Should have unlimited list access
   - Should be blocked from map views 
   - Should see padlock icons on map buttons
   - Direct map URLs should redirect to payment page
   - Can upgrade to £5 for full access
                ''')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating testuser3: {str(e)}')
            )