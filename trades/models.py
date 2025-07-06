from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.utils import timezone


class TradingAdvert(models.Model):
    """Simple trading advert for secondary capacity market trading"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_offer = models.BooleanField(default=True, help_text="True=Selling, False=Buying")
    capacity_mw = models.DecimalField(max_digits=7, decimal_places=2)
    delivery_year = models.IntegerField()
    price_gbp_per_kw_yr = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Leave blank for POA"
    )
    description = models.TextField(max_length=1000)
    contact_email = models.EmailField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    
    # Flexibility indicators
    capacity_flexible = models.BooleanField(default=False, help_text="Capacity amount is negotiable/flexible")
    price_estimate = models.BooleanField(default=False, help_text="Price is indicative/estimate only")
    
    # Contact preferences
    show_email_publicly = models.BooleanField(default=False, help_text="Show email address publicly for direct contact")
    
    # For Stripe payment tracking (Phase 2)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    
    # Edit tracking
    edit_count = models.IntegerField(default=0)
    last_edited = models.DateTimeField(null=True, blank=True)
    
    # Extension tracking
    original_expires_at = models.DateTimeField(null=True, blank=True)
    extension_count = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        if not self.original_expires_at:
            self.original_expires_at = self.expires_at
        super().save(*args, **kwargs)
    
    @property
    def type_display(self):
        return "Selling" if self.is_offer else "Buying"
    
    @property
    def price_display(self):
        if self.price_gbp_per_kw_yr:
            price_str = f"£{self.price_gbp_per_kw_yr:.2f}"
            if self.price_estimate:
                price_str += "*"
            return price_str
        return "POA"
    
    @property
    def capacity_display(self):
        capacity_str = f"{self.capacity_mw:.2f}MW"
        if self.capacity_flexible:
            capacity_str += "*"
        return capacity_str
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def can_edit(self):
        """Check if user can still edit (max 3 edits per payment period)"""
        return self.edit_count < 3
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        delta = self.expires_at - timezone.now()
        return delta.days if delta.days > 0 else 0
    
    @property
    def needs_expiry_reminder(self):
        """Check if advert needs 48-hour expiry reminder"""
        return self.days_until_expiry <= 2 and self.days_until_expiry > 0
    
    def extend_advert(self):
        """Extend advert for 30 more days from original expiry date"""
        if self.original_expires_at:
            # Calculate new expiry: original + (30 * number of extensions)
            self.extension_count += 1
            self.expires_at = self.original_expires_at + timedelta(days=30 * self.extension_count)
            self.edit_count = 0  # Reset edit count for new period
            self.save()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trading Advert"
        verbose_name_plural = "Trading Adverts"
    
    def __str__(self):
        return f"{self.type_display} {self.capacity_mw}MW for {self.delivery_year}"


class TradingMessage(models.Model):
    """Message sent between users about trading adverts"""
    
    advert = models.ForeignKey(TradingAdvert, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_trade_messages', null=True, blank=True)
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=100, blank=True, default='')
    message = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.sender_name} about {self.advert}"
