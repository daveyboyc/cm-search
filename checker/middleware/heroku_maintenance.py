"""
Middleware to serve custom maintenance page during Heroku maintenance mode.
"""
import os
from django.http import HttpResponse
from django.conf import settings


class HerokuMaintenanceMiddleware:
    """
    Middleware that serves a custom maintenance page when Heroku maintenance mode is enabled.
    This overrides Heroku's default maintenance page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if we're in Heroku maintenance mode
        # Heroku sets this header when maintenance mode is enabled
        if self.is_maintenance_mode(request):
            return self.serve_maintenance_page()
        
        response = self.get_response(request)
        return response

    def is_maintenance_mode(self, request):
        """
        Check if we should serve the maintenance page.
        This can be triggered by Heroku maintenance mode or a manual flag.
        """
        # Check for Heroku maintenance mode indicators
        # Heroku maintenance mode can be detected by various means
        
        # Option 1: Check for environment variable
        if os.environ.get('HEROKU_MAINTENANCE_MODE') == 'true':
            return True
            
        # Option 2: Check if we're being called from Heroku's maintenance system
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if 'heroku' in user_agent.lower() and 'maintenance' in user_agent.lower():
            return True
            
        # Option 3: Check for specific maintenance flag file
        maintenance_file = os.path.join(settings.BASE_DIR.parent, '.maintenance')
        if os.path.exists(maintenance_file):
            return True
            
        return False

    def serve_maintenance_page(self):
        """
        Serve the custom maintenance page HTML.
        """
        try:
            # Serve the static maintenance.html file directly
            maintenance_path = os.path.join(settings.BASE_DIR.parent, 'static', 'maintenance.html')
            with open(maintenance_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='text/html', status=503)
        except FileNotFoundError:
            # Fallback maintenance page
            fallback_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Maintenance Mode - Capacity Market Search</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            padding: 50px; 
            background: linear-gradient(135deg, #0ea5e9 0%, #1e40af 100%);
            color: white;
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 600px;
        }
        h1 { font-size: 2.5em; margin-bottom: 20px; }
        p { font-size: 1.2em; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Maintenance Mode</h1>
        <h2>Capacity Market Search</h2>
        <p>We're currently updating our systems to serve you better.</p>
        <p>We expect to be back online within the next 2-4 hours.</p>
        <p>Thank you for your patience!</p>
    </div>
</body>
</html>
            """
            return HttpResponse(fallback_html, content_type='text/html', status=503)