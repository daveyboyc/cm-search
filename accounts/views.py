from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.conf import settings
from .forms import UserRegistrationForm
from django.contrib.auth import login # Need login here now
from django.urls import reverse # Add this import for reverse URL lookups
import logging # Add logging import
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import UserProfile, RegistrationEmailRecord
from .utils import start_free_access_timer, get_or_create_user_profile, send_access_expired_reminder
import stripe
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.utils import timezone

# Create logger
logger = logging.getLogger(__name__)

def send_payment_confirmation_email(user):
    """Send payment confirmation email after successful subscription payment"""
    subject = "Payment Confirmed - Full Access Activated | Capacity Market Registry"
    
    # Get user profile for payment details
    try:
        profile = user.profile
        expiry_date = profile.paid_access_expiry_date.strftime('%B %d, %Y') if profile.paid_access_expiry_date else 'No expiry'
    except:
        expiry_date = 'Error retrieving date'
    
    # Plain text message
    message = f"""Dear {user.username},

🎉 PAYMENT CONFIRMED - FULL ACCESS ACTIVATED

Thank you for your £5.00 annual subscription! Your account now has full unlimited access to the Capacity Market Registry.

✅ What you now have access to:
• Unlimited searches across all technologies
• Full interactive map views with all 63,000+ capacity market components  
• Export functionality for search results
• Company and technology deep-dives with comprehensive statistics
• No time limits or restrictions
• Access to newly added data including latest NESO updates

🔗 Start exploring: https://capacitymarket.co.uk

Your subscription details:
• Amount: £5.00/year
• Access expires: {expiry_date}
• Auto-renewal: Yes (can be cancelled anytime)

If you experience any issues accessing the full features, please:
1. Log out completely
2. Log back in 
3. Clear your browser cache if needed

Thank you for supporting the Capacity Market Registry!

Best regards,
Capacity Market Search Team

---
Need help? Reply to this email or visit: https://capacitymarket.co.uk/account/
"""

    # HTML message
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #28a745; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .features {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; color: #666; }}
        ul {{ padding-left: 20px; }}
        .amount {{ font-size: 1.2em; font-weight: bold; color: #28a745; }}
        .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 Payment Confirmed!</h1>
        <p>Full Access Activated</p>
    </div>
    
    <div class="content">
        <p>Dear {user.username},</p>
        
        <div class="success">
            <strong>✅ Payment Confirmed: <span class="amount">£5.00/year</span></strong><br>
            Your account now has unlimited access to all features!
        </div>
        
        <div class="features">
            <h3>🔓 What you now have access to:</h3>
            <ul>
                <li><strong>Unlimited searches</strong> across all technologies</li>
                <li><strong>Full interactive map views</strong> with all 63,000+ capacity market components</li>
                <li><strong>Export functionality</strong> for search results and data downloads</li>
                <li><strong>Company and technology deep-dives</strong> with comprehensive statistics</li>
                <li><strong>No time limits</strong> or restrictions - use as much as you want</li>
                <li><strong>Access to newly added data</strong> including latest NESO updates</li>
            </ul>
        </div>
        
        <p><a href="https://capacitymarket.co.uk" class="btn">🔗 Start Exploring Now</a></p>
        
        <p><strong>Your subscription details:</strong></p>
        <ul>
            <li>Amount: £5.00/year</li>
            <li>Access expires: {expiry_date}</li>
            <li>Auto-renewal: Yes (can be cancelled anytime in Stripe)</li>
        </ul>
        
        <div style="border-left: 4px solid #17a2b8; padding-left: 15px; margin: 20px 0;">
            <p><strong>If you experience any issues accessing the full features:</strong></p>
            <ol>
                <li>Log out completely</li>
                <li>Log back in</li>
                <li>Clear your browser cache if needed</li>
            </ol>
        </div>
        
        <p>Thank you for supporting the Capacity Market Registry!</p>
        
        <p>Best regards,<br>
        <strong>Capacity Market Search Team</strong></p>
    </div>
    
    <div class="footer">
        <p>Need help? Reply to this email or visit: <a href="https://capacitymarket.co.uk/account/">https://capacitymarket.co.uk/account/</a></p>
    </div>
</body>
</html>
"""

    try:
        # Log email backend being used
        logger.info(f"Sending payment email using backend: {settings.EMAIL_BACKEND}")
        if hasattr(settings, 'EMAIL_HOST'):
            logger.info(f"Email host: {settings.EMAIL_HOST}, Port: {getattr(settings, 'EMAIL_PORT', 'not set')}")
        
        send_mail(
            subject=subject,
            message=message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"✅ Payment confirmation email sent successfully to {user.email}")
        return True
    except Exception as e:
        logger.error(f"❌ Error sending payment confirmation email to {user.email}: {e}")
        logger.error(f"Email settings - Backend: {settings.EMAIL_BACKEND}, From: {settings.DEFAULT_FROM_EMAIL}")
        return False

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            logger.info(f"Registration attempt with email: {email}")
            
            # Create an email record entry regardless of what happens next
            email_record = RegistrationEmailRecord(email=email)
            
            # Initialize existing_user to None
            existing_user = None
            
            # Check if a user with this email already exists but is inactive
            try:
                existing_user = User.objects.get(username=email)
                if not existing_user.is_active:
                    # User exists but is inactive, we can reuse this account
                    # Update the password to the new one
                    existing_user.set_password(form.cleaned_data['password1'])
                    existing_user.save()
                    user = existing_user
                    logger.info(f"Reusing inactive user: {user.username}")
                    email_record.user_created = True
                else:
                    # User exists and is active
                    logger.warning(f"Attempted registration with active email: {email}")
                    messages.error(request, f'The email address {email} is already registered and active. Please use the login page instead or try a different email address.')
                    
                    # Update email record with error
                    email_record.error_message = "Attempted registration with already active email"
                    email_record.save()
                    
                    return render(request, 'accounts/register.html', {'form': form})
            except User.DoesNotExist:
                # Create a new user
                user = form.save(commit=False) # Don't save to DB yet
                user.is_active = False # Deactivate account until email confirmation
                user.save() # Save user with is_active=False
                logger.info(f"Created inactive user: {user.username} with email: {user.email}")
                email_record.user_created = True

                # Send admin notification about new registration
                admin_subject = f'New User Registration: {email}'
                admin_message = f'A new user has registered with email: {email}. The account is pending email verification.'
                try:
                    send_mail(
                        admin_subject,
                        admin_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.DEFAULT_FROM_EMAIL],  # Send to admin email
                        fail_silently=True
                    )
                    logger.info(f"Admin notification sent for new registration: {email}")
                except Exception as e:
                    logger.error(f"Failed to send admin notification for new registration: {str(e)}")

            # Prepare email
            subject = 'Activate Your Account'
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_url = reverse('accounts:activate', kwargs={'uidb64': uid, 'token': token})
            activation_link = f"{settings.SITE_SCHEME}://{settings.SITE_DOMAIN}{activation_url}"
            
            # Save activation link to email record
            email_record.activation_link = activation_link
            
            logger.info(f"Generated activation link: {activation_link}")

            message = render_to_string('accounts/activation_email.html', {
                'user': user,
                'activation_link': activation_link,
            })

            try:
                # Log email settings being used
                logger.info(f"Email settings: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, "
                           f"USER={settings.EMAIL_HOST_USER}, FROM={settings.DEFAULT_FROM_EMAIL}")
                
                # Attempt to send email
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                logger.info(f"Successfully sent activation email to {user.email}")
                
                # Update and save email record
                email_record.save()
                
                messages.success(request, 'Registration successful! Please check your email to activate your account.')
                # Redirect to a confirmation pending page or home
                return redirect('accounts:registration_pending')
            except Exception as e:
                logger.error(f"Error sending activation email: {str(e)}", exc_info=True)
                messages.error(request, f'Error sending activation email: {e}')
                
                # Update email record with error
                email_record.error_message = f"Error sending activation email: {str(e)}"
                email_record.save()
                
                # Optionally delete the user or handle the error differently
                if not existing_user:  # Only delete if this was a new user
                    user.delete() # Simple cleanup on email error
                    logger.info(f"Deleted user {user.username} due to email sending failure")
                    email_record.user_created = False
                    email_record.save()
                return render(request, 'accounts/register.html', {'form': form})

        else:
            # Form is invalid, render it again with errors
            logger.info(f"Invalid registration form. Errors: {form.errors}")
            return render(request, 'accounts/register.html', {'form': form})
    else:
        # GET request, show the blank form
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user) # Log the user in after activation
        
        # Start the free access timer for the newly activated user
        start_free_access_timer(user)
        
        messages.success(request, 'Account activated successfully! You are now logged in.')
        
        # Update any email records for this user
        RegistrationEmailRecord.objects.filter(email=user.email).update(user_activated=True)
        
        # Send admin notification about successful activation
        admin_subject = f'User Account Activated: {user.email}'
        admin_message = f'The user with email: {user.email} has successfully activated their account.'
        try:
            send_mail(
                admin_subject,
                admin_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to admin email
                fail_silently=True
            )
            logger.info(f"Admin notification sent for account activation: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send admin notification for account activation: {str(e)}")
        
        # Redirect to home or a dashboard page
        return redirect('homepage') # Using the correct URL name
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        # Redirect to a page indicating activation failure
        return redirect('accounts:activation_failed')

# Add the missing views
def registration_pending(request):
    return render(request, 'accounts/registration_pending.html')

def activation_failed(request):
    return render(request, 'accounts/activation_failed.html')

def must_register(request):
    """Displays a page informing the user they must register to continue."""
    return render(request, 'accounts/must_register.html')

# --- Account Page --- #
@login_required
def account_view(request):
    """Displays the user's account page."""
    try:
        # Fetch the related UserProfile
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        # This should ideally not happen due to the signal, but handle it defensively
        logger.error(f"UserProfile not found for user {request.user.username}. Creating now.")
        profile = UserProfile.objects.create(user=request.user)
    
    # Start weekly trial if not already started and user doesn't have paid access
    if not profile.has_paid_access:
        from checker.access_control import get_user_access_level, start_trial_if_needed
        
        # Start trial usage timer for 2-tier system
        start_trial_if_needed(request.user)
        profile.refresh_from_db()
        
        # Check if trial has expired - show info but don't redirect from account page
        access_level = get_user_access_level(request.user)
        # Note: Removed redirect to allow account management even with expired trial
        
    # Check for payment success parameter
    payment_success = request.GET.get('payment') == 'success'
    
    context = {
        'user': request.user,
        'profile': profile,
        # Pass the specific boolean value to the template
        'has_paid_access': profile.is_paid_access_active,
        # Pass server-side timer data
        'free_access_start_time': profile.free_access_start_time,
        'free_access_time_remaining': profile.free_access_time_remaining,
        'is_free_access_expired': profile.is_free_access_expired,
        # Payment success feedback
        'payment_success': payment_success,
        'payment_just_completed': payment_success and profile.is_paid_access_active,
    }
    return render(request, 'accounts/account.html', context)

# --- Payment Required Page --- #
@login_required
def payment_required_view(request):
    """Displays a page informing the user their free access has expired."""
    logger.info(f"PAYMENT REQUIRED VIEW: User {request.user.username} accessing payment-required page")
    
    # TEMPORARY: Return simple HTML to bypass template issues
    from django.http import HttpResponse
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subscription Expired</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
            .btn {{ 
                background-color: #ffc107; 
                color: #000; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 5px; 
                font-size: 18px;
                display: inline-block;
                margin: 10px;
            }}
            .btn:hover {{ background-color: #e0a800; }}
        </style>
    </head>
    <body>
        <h1>🔒 Subscription Expired</h1>
        <p>Hello {request.user.username}!</p>
        <p>Your subscription has expired. Please renew to continue using the service.</p>
        
        <a href="/accounts/payment-selection/" class="btn">💳 Pay £5/Year for Unlimited Access</a>
        
        <p><a href="/accounts/account/">← Back to Account</a></p>
    </body>
    </html>
    """
    return HttpResponse(html)

# --- Stripe Payment Initiation --- #
@login_required
def payment_selection_view(request):
    """Displays the payment amount selection page."""
    context = {}
    return render(request, 'accounts/payment_selection.html', context)

@login_required
def initiate_payment_view(request):
    """Initiates the Stripe Checkout session for £5/year subscription."""
    if request.method != 'POST':
        # Redirect to payment selection page if accessed via GET
        return redirect('accounts:payment_selection')
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        # In 2-tier system, only one option: £5/year full access
        access_tier = request.POST.get('access_tier', 'full')
        
        # Always use yearly subscription price
        price_id = settings.STRIPE_YEARLY_ACCESS_PRICE_ID
        access_level = 'full'
        
        # Build absolute URLs for success/cancel
        success_url = request.build_absolute_uri(reverse('accounts:account') + '?payment=success')
        cancel_url = request.build_absolute_uri(reverse('accounts:payment_selection'))

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',  # Yearly subscription
            success_url=success_url,
            cancel_url=cancel_url,
            # Prefill email and include user ID and access level for webhook
            customer_email=request.user.email, 
            metadata={
                'user_id': request.user.id,
                'access_level': access_level,
                'subscription_type': 'yearly'
            }
        )
        # Redirect to Stripe Checkout
        return HttpResponseRedirect(checkout_session.url)
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session for user {request.user.id}: {str(e)}")
        messages.error(request, f'Could not initiate payment: {str(e)}')
        # Redirect back to payment selection page
        return redirect('accounts:payment_selection')

# --- Stripe Webhook Handler --- # 
@csrf_exempt 
@require_POST 
def stripe_webhook_view(request):
    """Listens for events from Stripe."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    # Get webhook secret from settings (MUST be set in production)
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None) 

    if not endpoint_secret:
        logger.error("Stripe webhook secret is not configured.")
        return HttpResponse(status=500) # Internal Server Error

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Stripe webhook event received: {event['type']}")
    except ValueError as e:
        # Invalid payload
        logger.error(f"Stripe webhook error (Invalid payload): {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Stripe webhook error (Invalid signature): {e}")
        return HttpResponse(status=400)
    except Exception as e:
        # Catch any other unexpected errors during event construction
        logger.error(f"Stripe webhook - Unexpected error during event construction: {e}", exc_info=True)
        return HttpResponse(status=500)

    # Handle subscription events for £5/year access
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.metadata.get('user_id')
        subscription_id = session.subscription  # Get subscription ID for yearly billing
        
        logger.info(f"Processing subscription checkout.session.completed for session ID: {session.id}")
        logger.debug(f"Session details: Status={session.status}, Subscription={subscription_id}, Metadata={session.metadata}")
        
        # For subscriptions, we need to check if the payment was successful
        if session.payment_status == 'paid' and user_id:
            logger.info(f"Subscription payment completed for user_id: {user_id}")
            try:
                user = User.objects.get(pk=user_id)
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created:
                    logger.warning(f"UserProfile created via webhook for user {user.username}")
                
                # Use subscription manager for proper duration handling
                from accounts.subscription_manager import SubscriptionManager
                profile = SubscriptionManager.create_subscription(profile, payment_amount=5.00)
                
                # Log subscription type for debugging
                sub_type = SubscriptionManager.get_subscription_type_display(user.email)
                logger.info(f"STRIPE WEBHOOK: Created {sub_type} for {user.email}")
                logger.info(f"Updated UserProfile for user {user.username}: yearly subscription active until {profile.paid_access_expiry_date}")
                
                # Queue payment confirmation email for background sending
                try:
                    # Send email in background to avoid blocking webhook response
                    from django.core.management import call_command
                    logger.info(f"Queuing payment confirmation email for {user.email}")
                    # For now, send immediately but log timing
                    import time
                    start_time = time.time()
                    send_payment_confirmation_email(user)
                    email_duration = time.time() - start_time
                    logger.info(f"Payment confirmation email sent to {user.email} in {email_duration:.2f}s")
                except Exception as email_error:
                    logger.error(f"Failed to send payment confirmation email to {user.email}: {email_error}")
                    # Don't fail webhook if email fails
                
            except User.DoesNotExist:
                logger.error(f"User with ID {user_id} not found from webhook metadata.")
            except Exception as e:
                logger.error(f"Error updating UserProfile for user_id {user_id}: {e}", exc_info=True)
                return HttpResponse(status=500)
        else:
            logger.warning(f"Subscription payment not completed or user_id missing. Payment status: {session.payment_status}")
    
    # Handle subscription renewal events
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        subscription_id = invoice.subscription
        customer_id = invoice.customer
        
        # For subscription renewals, extend the access period
        if subscription_id and customer_id:
            logger.info(f"Processing subscription renewal for subscription ID: {subscription_id}")
            
            try:
                # Find user by customer email (Stripe customer email should match user email)
                stripe.api_key = settings.STRIPE_SECRET_KEY
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.email
                
                if customer_email:
                    user = User.objects.get(email=customer_email)
                    profile = UserProfile.objects.get(user=user)
                    
                    # Extend subscription by 1 year from current expiry (or now if expired)
                    from datetime import timedelta
                    if profile.paid_access_expiry_date and profile.paid_access_expiry_date > timezone.now():
                        # Extend from current expiry date
                        profile.paid_access_expiry_date = profile.paid_access_expiry_date + timedelta(days=365)
                    else:
                        # Start new year from now if expired or no expiry set
                        profile.paid_access_expiry_date = timezone.now() + timedelta(days=365)
                    
                    profile.has_paid_access = True
                    profile.payment_amount = 5.00
                    profile.save()
                    
                    logger.info(f"Subscription renewed for user {user.username}: access extended until {profile.paid_access_expiry_date}")
                else:
                    logger.error(f"No email found for Stripe customer {customer_id}")
                    
            except User.DoesNotExist:
                logger.error(f"User not found for customer email: {customer_email}")
            except Exception as e:
                logger.error(f"Error processing subscription renewal: {e}", exc_info=True)
    
    else:
        logger.info(f"Received unhandled webhook event: {event['type']}")

    # Acknowledge receipt to Stripe
    return HttpResponse(status=200)

class CustomPasswordChangeView(PasswordChangeView):
    """Custom password change view with enhanced error logging."""
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('password_change_done')
    
    def form_invalid(self, form):
        """Log detailed information about the form errors."""
        logger.debug("Password change form invalid")
        
        # Log non-field errors
        if form.non_field_errors():
            logger.debug(f"Non-field errors: {form.non_field_errors()}")
        
        # Log field errors
        for field_name, errors in form.errors.items():
            logger.debug(f"Field '{field_name}' errors: {errors}")
        
        return super().form_invalid(form)
    
    def form_valid(self, form):
        logger.debug("Password change form valid")
        return super().form_valid(form)
