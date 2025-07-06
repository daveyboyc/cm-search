"""
Management command to test payment confirmation email functionality
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.views import send_payment_confirmation_email
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test payment confirmation email sending'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address to send test to')
        parser.add_argument('--user-id', type=int, help='User ID to send test for')
    
    def handle(self, *args, **options):
        email = options.get('email')
        user_id = options.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
                self.stdout.write(f"Testing payment email for user: {user.username} ({user.email})")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
                return
        elif email:
            try:
                user = User.objects.get(email=email)
                self.stdout.write(f"Testing payment email for user: {user.username} ({user.email})")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with email {email} not found"))
                return
        else:
            self.stdout.write(self.style.ERROR("Please provide either --email or --user-id"))
            return
        
        # Test email sending
        try:
            import time
            start_time = time.time()
            
            result = send_payment_confirmation_email(user)
            
            duration = time.time() - start_time
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Payment confirmation email sent successfully in {duration:.2f}s")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Payment confirmation email failed after {duration:.2f}s")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error sending payment confirmation email: {e}")
            )