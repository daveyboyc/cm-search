"""
Management command to check user access status
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from checker.access_control import get_user_access_level
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check user access status'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='5doubow@spamok.com', help='User email to check')
        
    def handle(self, *args, **options):
        email = options.get('email')
        
        try:
            user = User.objects.get(email=email)
            profile = UserProfile.objects.get(user=user)
            access_level = get_user_access_level(user)
            
            self.stdout.write(f"📋 User Status for {user.email}:")
            self.stdout.write(f"   Username: {user.username}")
            self.stdout.write(f"   Is Active: {user.is_active}")
            self.stdout.write(f"   Has Paid Access: {profile.has_paid_access}")
            self.stdout.write(f"   Paid Access Active: {profile.is_paid_access_active}")
            self.stdout.write(f"   Paid Access Expiry: {profile.paid_access_expiry_date}")
            self.stdout.write(f"   Access Level: {access_level}")
            
            # Check what the middleware would do
            if access_level == 'subscription_expired':
                self.stdout.write(self.style.WARNING(f"🚨 MIDDLEWARE SHOULD REDIRECT: User has subscription_expired access level"))
            elif access_level == 'full':
                self.stdout.write(self.style.SUCCESS(f"✅ MIDDLEWARE ALLOWS: User has full access"))
            elif access_level == 'trial':
                self.stdout.write(self.style.SUCCESS(f"✅ MIDDLEWARE ALLOWS: User has trial access"))
            elif access_level == 'trial_expired':
                self.stdout.write(self.style.WARNING(f"🔄 MIDDLEWARE REDIRECTS: User has trial_expired access level"))
            else:
                self.stdout.write(f"❓ UNKNOWN ACCESS LEVEL: {access_level}")
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User with email {email} not found"))
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ UserProfile not found for {email}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking user status: {e}"))