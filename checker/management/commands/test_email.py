"""
Email test command for verifying Mailgun configuration.

This command tests the email configuration by sending a test email
to verify that Mailgun is properly configured for weekly monitoring reports.

Usage:
    python manage.py test_email user@example.com
    python manage.py test_email user@example.com --check-config
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Test email configuration with Mailgun'
    
    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to send test to')
        parser.add_argument('--check-config', action='store_true', help='Only check configuration, don\'t send')
    
    def handle(self, *args, **options):
        email_to = options['email']
        check_only = options['check_config']
        
        self.stdout.write(self.style.SUCCESS('📧 Email Configuration Test'))
        
        # Check configuration
        self.stdout.write(f'\n🔧 Django Email Settings:')
        self.stdout.write(f'DEBUG: {settings.DEBUG}')
        self.stdout.write(f'EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        
        self.stdout.write(f'\n🔧 Mailgun Environment Variables:')
        mailgun_server = os.environ.get('MAILGUN_SMTP_SERVER', 'NOT SET')
        mailgun_port = os.environ.get('MAILGUN_SMTP_PORT', 'NOT SET')
        mailgun_login = os.environ.get('MAILGUN_SMTP_LOGIN', 'NOT SET')
        mailgun_password = 'SET' if os.environ.get('MAILGUN_SMTP_PASSWORD') else 'NOT SET'
        
        self.stdout.write(f'MAILGUN_SMTP_SERVER: {mailgun_server}')
        self.stdout.write(f'MAILGUN_SMTP_PORT: {mailgun_port}')
        self.stdout.write(f'MAILGUN_SMTP_LOGIN: {mailgun_login}')
        self.stdout.write(f'MAILGUN_SMTP_PASSWORD: {mailgun_password}')
        
        # Check if all required variables are set
        required_vars = ['MAILGUN_SMTP_SERVER', 'MAILGUN_SMTP_PORT', 'MAILGUN_SMTP_LOGIN', 'MAILGUN_SMTP_PASSWORD']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            self.stdout.write(self.style.ERROR(f'\n❌ Missing environment variables: {", ".join(missing_vars)}'))
            self.stdout.write('\n📋 To fix this, set these environment variables:')
            self.stdout.write('export MAILGUN_SMTP_SERVER=smtp.eu.mailgun.org')
            self.stdout.write('export MAILGUN_SMTP_PORT=587')
            self.stdout.write('export MAILGUN_SMTP_LOGIN=hello@capacitymarket.co.uk')
            self.stdout.write('export MAILGUN_SMTP_PASSWORD=your_mailgun_password')
            self.stdout.write('\n🔧 For Heroku:')
            self.stdout.write('heroku config:set MAILGUN_SMTP_SERVER=smtp.eu.mailgun.org')
            self.stdout.write('heroku config:set MAILGUN_SMTP_PORT=587')
            self.stdout.write('heroku config:set MAILGUN_SMTP_LOGIN=hello@capacitymarket.co.uk')
            self.stdout.write('heroku config:set MAILGUN_SMTP_PASSWORD=your_mailgun_password')
            
            if not check_only:
                self.stdout.write(self.style.ERROR('\n❌ Cannot send email - configuration incomplete'))
            return
        
        self.stdout.write(self.style.SUCCESS('\n✅ All Mailgun environment variables are set'))
        
        if check_only:
            self.stdout.write('\n📧 Configuration check complete - ready to send emails')
            return
        
        # Try to send test email
        self.stdout.write(f'\n📤 Sending test email to {email_to}...')
        
        subject = '📧 CMR Email Test - Mailgun Configuration'
        message = f"""
Hello!

This is a test email from the Capacity Market Monitoring System.

If you receive this email, Mailgun is configured correctly and ready for weekly monitoring reports.

Configuration Details:
• SMTP Server: {mailgun_server}
• Port: {mailgun_port}
• Login: {mailgun_login}
• From: {settings.DEFAULT_FROM_EMAIL}

Next Steps:
1. Set up weekly monitoring: python manage.py weekly_data_check --email={email_to}
2. Configure cron job for automated monitoring

Best regards,
Capacity Market Monitoring System
        """.strip()
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_to],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Test email sent successfully to {email_to}'))
            self.stdout.write('\n📋 If you don\'t receive the email, check:')
            self.stdout.write('• Spam/junk folder')
            self.stdout.write('• Mailgun dashboard for delivery logs')
            self.stdout.write('• Domain verification in Mailgun')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Email failed: {e}'))
            self.stdout.write('\n🔧 Troubleshooting:')
            self.stdout.write('• Verify Mailgun credentials')
            self.stdout.write('• Check domain verification')
            self.stdout.write('• Ensure sending domain is authorized')
            self.stdout.write('• Check Mailgun account status')