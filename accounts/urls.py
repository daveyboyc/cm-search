from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts' # Define an app namespace

urlpatterns = [
    path('register/', views.register, name='register'),
    # Add the activation URL
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    # Add missing routes
    path('registration-pending/', views.registration_pending, name='registration_pending'),
    path('activation-failed/', views.activation_failed, name='activation_failed'),
    path('must-register/', views.must_register, name='must_register'),
    # Add Account Page URL
    path('account/', views.account_view, name='account'),
    # Add Payment Required URL
    path('payment-required/', views.payment_required_view, name='payment_required'),
    # Add Payment Selection URL  
    path('payment-selection/', views.payment_selection_view, name='payment_selection'),
    # Add Payment Initiation URL
    path('initiate-payment/', views.initiate_payment_view, name='initiate_payment'),
    # Add Stripe Webhook URL (multiple paths for compatibility)
    path('stripe/webhook/', views.stripe_webhook_view, name='stripe_webhook'),
    path('stripe-webhook/', views.stripe_webhook_view, name='stripe_webhook_alt'),  # Alternative URL for compatibility
    # Custom password change view with better error reporting
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='custom_password_change'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='/accounts/password-reset-done/'
    ), name='password_reset'),
    path('password-reset-done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset-complete/'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
] 