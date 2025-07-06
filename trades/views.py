from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import TradingAdvert, TradingMessage
from .forms import TradingAdvertForm, TradingMessageForm
import stripe


class TradingAdvertListView(ListView):
    model = TradingAdvert
    template_name = 'trades/list.html'
    context_object_name = 'adverts'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = TradingAdvert.objects.filter(
            is_active=True,
            expires_at__gte=timezone.now()
        ).select_related('user')
        
        # Filter by tab
        tab = self.request.GET.get('tab', 'selling')
        if tab == 'buying':
            queryset = queryset.filter(is_offer=False)
        else:
            queryset = queryset.filter(is_offer=True)
        
        # Handle sorting
        sort_by = self.request.GET.get('sort', '-created_at')  # Default: newest first
        
        valid_sorts = {
            'date_asc': 'created_at',
            'date_desc': '-created_at', 
            'mw_asc': 'capacity_mw',
            'mw_desc': '-capacity_mw',
            'year_asc': 'delivery_year',
            'year_desc': '-delivery_year',
            'price_asc': 'price_gbp_per_kw_yr',
            'price_desc': '-price_gbp_per_kw_yr'
        }
        
        if sort_by in valid_sorts:
            # Handle NULL prices (put at end for price sorts)
            if 'price' in sort_by:
                if sort_by == 'price_asc':
                    queryset = queryset.order_by('price_gbp_per_kw_yr', 'created_at')
                else:
                    queryset = queryset.order_by('-price_gbp_per_kw_yr', 'created_at')
            else:
                queryset = queryset.order_by(valid_sorts[sort_by])
        else:
            queryset = queryset.order_by('-created_at')  # Default
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get counts for tabs
        all_adverts = TradingAdvert.objects.filter(
            is_active=True,
            expires_at__gte=timezone.now()
        )
        context['selling_count'] = all_adverts.filter(is_offer=True).count()
        context['buying_count'] = all_adverts.filter(is_offer=False).count()
        context['current_tab'] = self.request.GET.get('tab', 'selling')
        return context


class TradingAdvertCreateView(CreateView):
    model = TradingAdvert
    form_class = TradingAdvertForm
    template_name = 'trades/create.html'
    success_url = reverse_lazy('trades:list')
    
    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['contact_email'] = self.request.user.email
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_invalid(self, form):
        print(f"🔥 FORM INVALID DEBUG:")
        print(f"Form errors: {form.errors}")
        print(f"Non-field errors: {form.non_field_errors()}")
        return super().form_invalid(form)
    
    def form_valid(self, form):
        contact_email = form.cleaned_data['contact_email']
        
        # Debug info
        print(f"🔥 FORM SUBMISSION DEBUG:")
        print(f"DEBUG: {settings.DEBUG}")
        print(f"STRIPE_PRICE_ID: {settings.STRIPE_TRADING_ADVERT_PRICE_ID}")
        print(f"User authenticated: {self.request.user.is_authenticated}")
        print(f"Contact email: {contact_email}")
        
        # Check if user is already logged in
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
            messages.success(self.request, "✅ Advert posted successfully!")
        else:
            # Try to find existing user by email
            try:
                user = User.objects.get(email=contact_email)
                form.instance.user = user
                messages.success(
                    self.request, 
                    f"✅ Advert posted successfully! Using your existing account for {contact_email}"
                )
            except User.DoesNotExist:
                # Create new user account
                username = contact_email.split('@')[0]
                # Ensure unique username
                if User.objects.filter(username=username).exists():
                    username = f"{username}_{User.objects.count()}"
                
                # Use provided password or generate random one
                password = form.cleaned_data.get('password')
                if not password:
                    from django.utils.crypto import get_random_string
                    password = get_random_string(12)
                
                user = User.objects.create_user(
                    username=username,
                    email=contact_email,
                    password=password
                )
                form.instance.user = user
                messages.success(
                    self.request, 
                    f"✅ Advert posted successfully! Account created for {contact_email} - "
                    f"you can now manage your adverts by signing in."
                )
        
        # Save the advert as unpaid first
        form.instance.is_paid = False
        form.instance.is_active = False  # Only activate after payment
        
        # Save the advert to get an ID
        advert = form.save()
        
        # Set up Stripe API key
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        # Check if we're in development and skip payment
        # For now, bypass payment if using the default/placeholder price ID
        if settings.STRIPE_TRADING_ADVERT_PRICE_ID == 'price_trading_advert_5gbp':
            print("🧪 DEVELOPMENT MODE: Bypassing payment (using placeholder price ID)")
            # For local development without real Stripe setup
            advert.is_paid = True
            advert.is_active = True
            advert.save()
            
            messages.success(
                self.request, 
                f"✅ Advert posted successfully! Your listing is now live and will expire in 30 days. "
                f"(Development mode - no payment required)"
            )
            return redirect('trades:list')
        
        # Create Stripe checkout session
        try:
            success_url = self.request.build_absolute_uri(
                reverse('trades:payment_success', args=[advert.pk])
            )
            cancel_url = self.request.build_absolute_uri(
                reverse('trades:payment_cancel', args=[advert.pk])
            )
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': settings.STRIPE_TRADING_ADVERT_PRICE_ID,
                    'quantity': 1,
                }],
                mode='payment',  # One-time payment
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=contact_email,
                metadata={
                    'advert_id': advert.id,
                    'user_id': advert.user.id,
                    'type': 'trading_advert'
                }
            )
            
            # Redirect to Stripe checkout
            return redirect(checkout_session.url)
            
        except stripe.error.StripeError as e:
            # If Stripe fails, delete the unpaid advert and show error
            advert.delete()
            messages.error(
                self.request, 
                f"Payment setup failed. This may be because the Stripe product hasn't been created yet. "
                f"In production, run: python manage.py create_trading_stripe_product. Error: {e}"
            )
            return self.form_invalid(form)


class TradingAdvertDetailView(DetailView):
    model = TradingAdvert
    template_name = 'trades/detail.html'
    context_object_name = 'advert'
    
    def get_queryset(self):
        # Only show active adverts
        return TradingAdvert.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message_form'] = TradingMessageForm()
        
        # Check if current user can edit this advert
        advert = self.get_object()
        if self.request.user.is_authenticated and advert.user == self.request.user:
            context['can_edit'] = advert.can_edit
            context['edits_remaining'] = 3 - advert.edit_count
        else:
            context['can_edit'] = False
            context['edits_remaining'] = 0
            
        return context


class TradingAdvertEditView(LoginRequiredMixin, UpdateView):
    model = TradingAdvert
    form_class = TradingAdvertForm
    template_name = 'trades/edit.html'
    
    def get_queryset(self):
        # Only allow editing own active adverts
        return TradingAdvert.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def dispatch(self, request, *args, **kwargs):
        # Get the object early to check edit permissions
        try:
            self.object = self.get_object()
            if not self.object.can_edit:
                messages.error(
                    request,
                    f"You have used all 3 edits for this advert. You can extend the listing to get 3 more edits."
                )
                return redirect('trades:detail', pk=self.object.pk)
        except:
            pass
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Track the edit
        form.instance.edit_count += 1
        form.instance.last_edited = timezone.now()
        
        messages.success(
            self.request,
            f"✅ Advert updated successfully! You have {3 - form.instance.edit_count} edits remaining."
        )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('trades:detail', kwargs={'pk': self.object.pk})


def send_message_view(request, pk):
    """Handle sending messages about trading adverts"""
    advert = get_object_or_404(TradingAdvert, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = TradingMessageForm(request.POST)
        if form.is_valid():
            # Create message record
            message = form.save(commit=False)
            message.advert = advert
            message.sender = request.user if request.user.is_authenticated else None
            message.sender_name = message.sender_email.split('@')[0] if not message.sender_name else message.sender_name
            message.save()
            
            # Send email to advert owner
            try:
                subject = f"Trading Inquiry: {advert.type_display} {advert.capacity_mw}MW for {advert.delivery_year}"
                email_message = f"""
You have received a new inquiry about your capacity market listing:

Listing: {advert.type_display} {advert.capacity_display} for {advert.delivery_year}
Price: {advert.price_display}/kW/year

From: {message.sender_name}
Email: {message.sender_email}

Message:
{message.message}

---
Listing Reference: #{advert.pk}
Reply directly to {message.sender_email} to continue the conversation.

This message was sent via CapacityMarket.co.uk Trading Board.
                """.strip()
                
                # Debug info for console
                print(f"\n🔥 SENDING EMAIL TO: {advert.contact_email}")
                print(f"📧 FROM: {settings.DEFAULT_FROM_EMAIL}")
                print(f"📝 SUBJECT: {subject}")
                print(f"💬 MESSAGE:\n{email_message}")
                print("="*50)
                
                send_mail(
                    subject=subject,
                    message=email_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[advert.contact_email],
                    fail_silently=False,
                )
                
                messages.success(request, f"✅ Your message has been sent successfully to {advert.contact_email}!")
                
            except Exception as e:
                print(f"❌ EMAIL ERROR: {e}")
                messages.error(request, f"❌ Message saved but email delivery failed: {e}")
            
            return redirect('trades:list')
    else:
        # Pre-populate email if user is logged in
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['sender_email'] = request.user.email
        
        form = TradingMessageForm(initial=initial_data)
    
    return render(request, 'trades/send_message.html', {
        'advert': advert,
        'form': form
    })


def send_confirmation_email(advert):
    """Send confirmation email to advert poster with expiry details"""
    try:
        subject = f"Advert Posted Successfully - {advert.type_display} {advert.capacity_display}"
        
        email_message = f"""
Your capacity market advert has been posted successfully and is now live!

ADVERT DETAILS:
Type: {advert.type_display}
Capacity: {advert.capacity_display}
Delivery Year: {advert.delivery_year}
Price: {advert.price_display}/kW/year
Description: {advert.description}

LISTING INFORMATION:
• Posted: {advert.created_at.strftime('%d %B %Y at %H:%M')}
• Expires: {advert.expires_at.strftime('%d %B %Y at %H:%M')} (30 days from posting)
• Reference ID: #{advert.pk}

EDIT PERMISSIONS:
You can edit your advert up to 3 times during this 30-day period. Simply log in to your account and visit the trading board to manage your listings.

EXPIRY REMINDER:
You will receive a reminder email 48 hours before your advert expires with the option to extend it for another 30 days.

View your advert: https://capacitymarket.co.uk/trades/{advert.pk}/

Thank you for using CapacityMarket.co.uk Trading Board!

---
This is an automated message. Please do not reply to this email.
For support, contact us through the website.
        """.strip()
        
        print(f"\n📧 SENDING CONFIRMATION EMAIL TO: {advert.contact_email}")
        print(f"📝 SUBJECT: {subject}")
        print("=" * 50)
        
        send_mail(
            subject=subject,
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[advert.contact_email],
            fail_silently=False,
        )
        
        print("✅ Confirmation email sent successfully")
        
    except Exception as e:
        print(f"❌ CONFIRMATION EMAIL ERROR: {e}")


def payment_success(request, pk):
    """Handle successful payment for trading advert"""
    advert = get_object_or_404(TradingAdvert, pk=pk)
    
    # Activate the advert (payment will be confirmed via webhook)
    advert.is_paid = True
    advert.is_active = True
    advert.save()
    
    # Send confirmation email
    send_confirmation_email(advert)
    
    messages.success(
        request, 
        f"🎉 Payment successful! Your advert is now live and will appear in the listings. "
        f"Check your email for confirmation details."
    )
    
    return redirect('trades:list')


def payment_cancel(request, pk):
    """Handle cancelled payment for trading advert"""
    advert = get_object_or_404(TradingAdvert, pk=pk)
    
    # Delete the unpaid advert
    advert.delete()
    
    messages.info(
        request, 
        "Payment was cancelled. Your advert was not posted. "
        "You can try again anytime."
    )
    
    return redirect('trades:create')


def extend_advert_view(request, pk):
    """Handle advert extension payment"""
    advert = get_object_or_404(TradingAdvert, pk=pk, is_active=True)
    
    # Check if user owns this advert
    if not request.user.is_authenticated or advert.user != request.user:
        messages.error(request, "You can only extend your own adverts.")
        return redirect('trades:detail', pk=pk)
    
    # Check if advert is close to expiry (allow extension within 7 days of expiry)
    days_until_expiry = advert.days_until_expiry
    if days_until_expiry > 7:
        messages.error(
            request, 
            f"You can only extend adverts within 7 days of expiry. "
            f"Your advert expires in {days_until_expiry} days."
        )
        return redirect('trades:detail', pk=pk)
    
    # Set up Stripe API key
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # Check if we're in development mode
    if settings.STRIPE_TRADING_ADVERT_PRICE_ID == 'price_trading_advert_5gbp':
        print("🧪 DEVELOPMENT MODE: Bypassing extension payment")
        advert.extend_advert()
        messages.success(
            request,
            f"✅ Advert extended successfully! Your listing now expires on "
            f"{advert.expires_at.strftime('%d %B %Y')} and you have 3 new edits available. "
            f"(Development mode - no payment required)"
        )
        return redirect('trades:detail', pk=pk)
    
    # Create Stripe checkout session for extension
    try:
        success_url = request.build_absolute_uri(
            reverse('trades:extension_success', args=[advert.pk])
        )
        cancel_url = request.build_absolute_uri(
            reverse('trades:extension_cancel', args=[advert.pk])
        )
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_TRADING_ADVERT_PRICE_ID,
                'quantity': 1,
            }],
            mode='payment',  # One-time payment
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=advert.contact_email,
            metadata={
                'advert_id': advert.id,
                'user_id': advert.user.id,
                'type': 'trading_advert_extension'
            }
        )
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url)
        
    except stripe.error.StripeError as e:
        messages.error(
            request, 
            f"Extension payment setup failed: {e}"
        )
        return redirect('trades:detail', pk=pk)


def extension_success(request, pk):
    """Handle successful extension payment"""
    advert = get_object_or_404(TradingAdvert, pk=pk)
    
    # Extend the advert (this resets edit count to 0 and extends expiry)
    advert.extend_advert()
    
    messages.success(
        request,
        f"🎉 Extension payment successful! Your advert has been extended until "
        f"{advert.expires_at.strftime('%d %B %Y')} and you now have 3 new edits available."
    )
    
    return redirect('trades:detail', pk=pk)


def extension_cancel(request, pk):
    """Handle cancelled extension payment"""
    advert = get_object_or_404(TradingAdvert, pk=pk)
    
    messages.info(
        request,
        "Extension payment was cancelled. Your advert will still expire as scheduled. "
        "You can try extending again anytime before it expires."
    )
    
    return redirect('trades:detail', pk=pk)
