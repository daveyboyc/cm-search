from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from trades.models import TradingAdvert


class Command(BaseCommand):
    help = 'Send expiry reminder emails for adverts expiring within 48 hours'

    def handle(self, *args, **options):
        # Find adverts that need expiry reminders (48 hours or less until expiry)
        adverts_needing_reminder = TradingAdvert.objects.filter(
            is_active=True,
            expires_at__lte=timezone.now() + timezone.timedelta(hours=48),
            expires_at__gt=timezone.now()
        )
        
        # Filter to only those that actually need reminders
        adverts_to_remind = [ad for ad in adverts_needing_reminder if ad.needs_expiry_reminder]
        
        self.stdout.write(f"Found {len(adverts_to_remind)} adverts needing expiry reminders")
        
        success_count = 0
        error_count = 0
        
        for advert in adverts_to_remind:
            try:
                self.send_expiry_reminder(advert)
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Sent reminder for advert #{advert.pk}")
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to send reminder for advert #{advert.pk}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Summary: {success_count} sent, {error_count} failed"
            )
        )
    
    def send_expiry_reminder(self, advert):
        """Send expiry reminder email with extension option"""
        hours_remaining = (advert.expires_at - timezone.now()).total_seconds() / 3600
        
        subject = f"Your Trading Advert Expires Soon - {advert.type_display} {advert.capacity_display}"
        
        email_message = f"""
Your capacity market advert is expiring soon!

ADVERT DETAILS:
Type: {advert.type_display}
Capacity: {advert.capacity_display}
Delivery Year: {advert.delivery_year}
Price: {advert.price_display}/kW/year
Reference ID: #{advert.pk}

EXPIRY NOTICE:
⏰ Your advert expires in approximately {hours_remaining:.1f} hours
📅 Expiry Date: {advert.expires_at.strftime('%d %B %Y at %H:%M')}

EXTEND YOUR LISTING:
Don't let your advert expire! You can extend it for another 30 days for just £5.

Benefits of extending:
• Your advert stays live for 30 more days from the original expiry date
• You get 3 new edits to update your listing
• No need to re-enter all your information

🔗 Extend Now: https://capacitymarket.co.uk/trades/{advert.pk}/extend/

CURRENT LISTING:
🔗 View/Edit: https://capacitymarket.co.uk/trades/{advert.pk}/

If you don't extend, your advert will be automatically deactivated when it expires.

Thank you for using CapacityMarket.co.uk Trading Board!

---
This is an automated reminder. Please do not reply to this email.
For support, contact us through the website.
        """.strip()
        
        send_mail(
            subject=subject,
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[advert.contact_email],
            fail_silently=False,
        )