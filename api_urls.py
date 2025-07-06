"""
API URLs for api.capacitymarket.co.uk subdomain
Clean, RESTful API endpoints for programmatic access
"""
from django.urls import path
from checker import views_api

urlpatterns = [
    # Main search endpoint
    path('search/', views_api.api_search, name='api_search'),
    
    # Resource-specific endpoints
    path('companies/', views_api.api_companies, name='api_companies'),
    path('companies/<str:company_name>/', views_api.api_company_detail, name='api_company_detail'),
    
    path('technologies/', views_api.api_technologies, name='api_technologies'),
    path('technologies/<str:technology_name>/', views_api.api_technology_detail, name='api_technology_detail'),
    
    path('components/', views_api.api_components, name='api_components'),
    path('components/<int:component_id>/', views_api.api_component_detail, name='api_component_detail'),
    
    path('locations/', views_api.api_locations, name='api_locations'),
    path('locations/<int:location_id>/', views_api.api_location_detail, name='api_location_detail'),
    
    path('cmus/', views_api.api_cmus, name='api_cmus'),
    path('cmus/<str:cmu_id>/', views_api.api_cmu_detail, name='api_cmu_detail'),
    
    # API documentation
    path('', views_api.api_root, name='api_root'),
    path('docs/', views_api.api_docs, name='api_docs'),
    path('health/', views_api.api_health, name='api_health'),
    
    # Catch-all for any other path - return JSON instead of OK
    path('<path:path>', views_api.api_catch_all, name='api_catch_all'),
]