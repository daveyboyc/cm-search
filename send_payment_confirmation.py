#!/usr/bin/env python3
"""
Send payment confirmation email to user
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.core.mail import send_mail
from django.conf import settings

def send_payment_confirmation_email(email):
    """Send payment confirmation email to user"""
    
    try:
        user = User.objects.get(email=email)
        profile = UserProfile.objects.get(user=user)
        
        print(f'📧 Sending payment confirmation to {email}')
        
        subject = "Payment Confirmed - Full Access Activated | Capacity Market Registry"
        
        message = f"""Dear {user.username},

🎉 PAYMENT CONFIRMED - FULL ACCESS ACTIVATED

Thank you for your £5.00 payment! Your account now has full unlimited access to the Capacity Market Registry.

✅ What you now have access to:
• Unlimited searches across all technologies
• Full map views with all capacity market data  
• Export functionality for search results
• No time limits or restrictions
• Access to all 63,000+ capacity market components

🔗 Start exploring: https://capacitymarket.co.uk

Your access is perpetual - no expiry date, no recurring charges.

If you experience any issues accessing the full features, please:
1. Log out completely
2. Log back in 
3. Clear your browser cache if needed

Thank you for supporting the Capacity Market Registry!

Best regards,
The Capacity Market Registry Team

---
Need help? Reply to this email or visit: https://capacitymarket.co.uk/account/
"""

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
            <strong>✅ Payment Confirmed: <span class="amount">£5.00</span></strong><br>
            Your account now has unlimited access to all features!
        </div>
        
        <div class="features">
            <h3>🔓 What you now have access to:</h3>
            <ul>
                <li><strong>Unlimited searches</strong> across all technologies</li>
                <li><strong>Full map views</strong> with all capacity market data</li>
                <li><strong>Export functionality</strong> for search results</li>
                <li><strong>No time limits</strong> or restrictions</li>
                <li><strong>Access to all 63,000+</strong> capacity market components</li>
            </ul>
        </div>
        
        <p><a href="https://capacitymarket.co.uk" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔗 Start Exploring Now</a></p>
        
        <p><strong>Your access is perpetual</strong> - no expiry date, no recurring charges.</p>
        
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
        <strong>The Capacity Market Registry Team</strong></p>
    </div>
    
    <div class="footer">
        <p>Need help? Reply to this email or visit: <a href="https://capacitymarket.co.uk/account/">https://capacitymarket.co.uk/account/</a></p>
    </div>
</body>
</html>
"""

        # Send the email
        send_mail(
            subject=subject,
            message=message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        print(f'✅ Payment confirmation email sent successfully!')
        print(f'   Subject: {subject}')
        print(f'   To: {email}')
        
        return True
        
    except User.DoesNotExist:
        print(f'❌ User not found: {email}')
        return False
    except Exception as e:
        print(f'❌ Error sending email: {e}')
        return False

if __name__ == "__main__":
    send_payment_confirmation_email('davidcrawford83@gmail.com')