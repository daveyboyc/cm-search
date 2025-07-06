from django import forms
from .models import TradingAdvert, TradingMessage
from datetime import datetime
from django.contrib.auth.models import User


class TradingAdvertForm(forms.ModelForm):
    # Add password field for new users (not saved to model)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Required if you don't have an account yet"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Confirm your password"
    )
    
    class Meta:
        model = TradingAdvert
        fields = ['is_offer', 'capacity_mw', 'capacity_flexible', 'delivery_year', 'price_gbp_per_kw_yr', 'price_estimate', 'description', 'contact_email', 'show_email_publicly']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'capacity_mw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_gbp_per_kw_yr': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_offer': forms.RadioSelect(choices=[(True, 'Selling'), (False, 'Buying')])
        }
        labels = {
            'is_offer': 'I am',
            'capacity_mw': 'Capacity (MW)',
            'capacity_flexible': 'Capacity is negotiable/flexible',
            'delivery_year': 'Delivery Year',
            'price_gbp_per_kw_yr': 'Price (£/kW/year) - Leave blank for POA',
            'price_estimate': 'Price is indicative/estimate only',
            'contact_email': 'Contact Email',
            'show_email_publicly': 'Show my email publicly for direct contact',
        }
    
    def clean_capacity_mw(self):
        capacity = self.cleaned_data['capacity_mw']
        if capacity <= 0:
            raise forms.ValidationError("Capacity must be greater than 0")
        return capacity
    
    def clean_delivery_year(self):
        year = self.cleaned_data['delivery_year']
        current_year = datetime.now().year
        if year < current_year + 1:
            raise forms.ValidationError(f"Delivery year must be {current_year + 1} or later")
        if year > current_year + 10:
            raise forms.ValidationError(f"Delivery year cannot be more than 10 years in the future")
        return year
    
    def clean_price_gbp_per_kw_yr(self):
        price = self.cleaned_data.get('price_gbp_per_kw_yr')
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative")
        return price
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If user is authenticated, hide password fields
        if self.user and self.user.is_authenticated:
            del self.fields['password']
            del self.fields['confirm_password']
    
    def clean(self):
        cleaned_data = super().clean()
        contact_email = cleaned_data.get('contact_email')
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        print(f"🔥 FORM CLEAN DEBUG:")
        print(f"Contact email: {contact_email}")
        print(f"Password provided: {bool(password)}")
        print(f"User authenticated: {bool(self.user and self.user.is_authenticated)}")
        
        # If user is not authenticated, check password requirements
        if not (self.user and self.user.is_authenticated):
            # Check if user exists with this email
            if contact_email and User.objects.filter(email=contact_email).exists():
                # User exists - no password needed, they can login separately
                print("User exists - no password needed")
                pass
            else:
                # New user - password required
                print("New user - checking password requirements")
                if not password:
                    print("ERROR: Password is required")
                    raise forms.ValidationError("Password is required for new accounts")
                if password != confirm_password:
                    print("ERROR: Passwords do not match")
                    raise forms.ValidationError("Passwords do not match")
                if len(password) < 8:
                    print("ERROR: Password too short")
                    raise forms.ValidationError("Password must be at least 8 characters long")
        
        print("Form validation passed!")
        return cleaned_data


class TradingMessageForm(forms.ModelForm):
    class Meta:
        model = TradingMessage
        fields = ['sender_email', 'message']
        widgets = {
            'sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Your message about this capacity listing...'}),
        }
        labels = {
            'sender_email': 'Your Email',
            'message': 'Message',
        }
    
    def clean_message(self):
        message = self.cleaned_data['message']
        if len(message.strip()) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long")
        return message