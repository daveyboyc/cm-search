"""
Management command to simulate rapid renewal/expiry cycles for testing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Simulate renewal/expiry cycles for testing'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='5doubow@spamok.com', help='User email')
        parser.add_argument('--cycles', type=int, default=3, help='Number of cycles to simulate')
        parser.add_argument('--cycle-minutes', type=int, default=2, help='Minutes per cycle')
        
    def handle(self, *args, **options):
        email = options.get('email')
        cycles = options.get('cycles')
        cycle_minutes = options.get('cycle_minutes')
        
        try:
            user = User.objects.get(email=email)
            profile = UserProfile.objects.get(user=user)
            
            self.stdout.write(f"🔄 Starting renewal/expiry simulation for {email}")
            self.stdout.write(f"   Will run {cycles} cycles of {cycle_minutes} minutes each")
            
            for cycle in range(1, cycles + 1):
                self.stdout.write(f"\n--- CYCLE {cycle} ---")
                
                # RENEW: Set subscription active
                profile.has_paid_access = True
                profile.paid_access_expiry_date = timezone.now() + timedelta(minutes=cycle_minutes)
                profile.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f"✅ RENEWED: Subscription active until {profile.paid_access_expiry_date.strftime('%H:%M:%S')}"
                ))
                
                # Wait for half the cycle
                wait_seconds = (cycle_minutes * 60) // 2
                self.stdout.write(f"⏰ Waiting {wait_seconds} seconds before checking...")
                time.sleep(wait_seconds)
                
                # Check status
                profile.refresh_from_db()
                if profile.is_paid_access_active:
                    self.stdout.write(self.style.SUCCESS("✅ Still active (as expected)"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Already expired (unexpected)"))
                
                # Wait for expiry
                remaining = cycle_minutes * 60 - wait_seconds
                self.stdout.write(f"⏰ Waiting {remaining} more seconds for expiry...")
                time.sleep(remaining + 5)  # Add 5 seconds buffer
                
                # Check if expired
                profile.refresh_from_db()
                if not profile.is_paid_access_active:
                    self.stdout.write(self.style.WARNING("🔒 EXPIRED: Subscription has expired"))
                    self.stdout.write(f"   Access level: {profile.user.profile.get_access_level()}")
                else:
                    self.stdout.write(self.style.ERROR("❌ Still active (should be expired)"))
                
                if cycle < cycles:
                    self.stdout.write("\n🔄 Simulating renewal in 5 seconds...")
                    time.sleep(5)
            
            self.stdout.write(self.style.SUCCESS("\n✅ Simulation completed!"))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User {email} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))