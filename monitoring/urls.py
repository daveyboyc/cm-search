"""
URLs for monitoring dashboard
"""
from django.urls import path
from . import simple_monitor

app_name = 'monitoring'

urlpatterns = [
    path('', simple_monitor.simple_dashboard, name='dashboard'),
    path('simple-api/', simple_monitor.simple_api, name='simple_api'),
]