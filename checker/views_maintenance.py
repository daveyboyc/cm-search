from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
import os

def maintenance_view(request):
    """
    View for the maintenance page.
    Serves the static maintenance.html file directly.
    """
    try:
        # Try to serve the static maintenance.html file
        maintenance_path = os.path.join(settings.BASE_DIR.parent, 'static', 'maintenance.html')
        with open(maintenance_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html', status=503)
    except FileNotFoundError:
        # Fallback to template rendering
        return render(request, 'maintenance.html', status=503)