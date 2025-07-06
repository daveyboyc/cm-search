from django.urls import path
from django.shortcuts import redirect
from . import views
from .utils import slugify
from .services.component_detail import get_component_details
from .debug_views import debug_component_duplicates
from .services.component_search import search_components_service  # OLD
from .views_search_optimized import search_components_optimized, homepage_view  # NEW OPTIMIZED
from .services.component_search_optimized_v2 import search_components_optimized_v2
from .services.company_search import cmu_detail
from .views import donation_page, create_checkout_session, donation_success, donation_cancel, help_view
from django.http import HttpResponse


# Import new map test view
# from .views_new_map_test import map_search_fixed_view
# Import search GeoJSON view
from .views_search_geojson import search_results_geojson
# Import batch API views
from .views_batch_api import batch_geojson_api, optimized_geojson_stream
# Import map search results view
from .views_map_results import map_search_results_view
# Import test location search view
# from .views_location_test import test_location_search, test_location_search_html, test_location_search_styled
# Import location detail view
from .views_location_detail import location_detail
# Import optimized company view
from .views_company_optimized import company_detail_optimized, company_detail_map
from .views_cmu_map import cmu_detail_map
# Import optimized technology view
from .views_technology_optimized import technology_detail_optimized, technology_detail_map
# Import optimized CMU view
from .views_cmu_optimized import cmu_detail_optimized
# Import SEO-friendly views
from .views_seo import location_detail_by_name_seo, company_detail_seo, technology_detail_seo
# REMOVED: Statistics view (caused massive Supabase egress)
# from .views_statistics import statistics_view_optimized
# Import optimized list views
# Import unified test views
# from .views_unified_test import unified_search_map_test, unified_search_map_google_test, test_google_maps, search_with_map, search_results_with_map, search_results_with_map_real, search_results_with_map_google
from .views_lists_optimized import company_list_optimized, technology_list_optimized
from .views_search_map_simple import search_map_view_simple
# Import map explorer view
from .views_map_explorer import map_explorer_view
# Import filtered subtypes API
from .views_subtypes import get_filtered_subtypes
from .views_company_technologies import get_company_technologies
# Import search filters API for lazy loading
from .views_search_filters_api import search_filters_api
# Import minimal SEO views for bots
from .views_seo_minimal import (
    company_seo_minimal, technology_seo_minimal, 
    location_seo_minimal, component_seo_minimal,
    search_seo_minimal, cmu_seo_minimal
)

# Import cache monitoring views
from .views_cache_monitor import cache_monitor_api, cache_monitor_dashboard

urlpatterns = [
    # Legacy search - redirect to new search
    path("components/", lambda request: redirect('search_map_view', permanent=True)),

    # Help endpoint
    path("help/", help_view, name="help"),
    path("help/<str:section>/", help_view, name="help_section"),
    
    # Test donation page - accessible to everyone
    # path("test-access-donation/", views_test.test_donation_view, name="test_donation"),

    # Donation endpoints
    path('donate/', donation_page, name='donation_page'),
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('donation-success/', donation_success, name='donation_success'),
    path('donation-cancel/', donation_cancel, name='donation_cancel'),
    
    # Test Access Donation endpoints
    path('test-access-donation/', views.test_access_donation_page, name='test_access_donation_page'),
    path('create-test-access-checkout/', views.create_test_access_checkout, name='create_test_access_checkout'),
    path('test-access-success/', views.test_access_success, name='test_access_success'),
    path('test-access-status/', views.test_access_status, name='test_access_status'),

    # HTMX endpoints
    path("api/company-years/<str:company_id>/<str:year>/",
         views.htmx_company_years, name="htmx_company_years"),
    path("api/company-years/<str:company_id>/<str:year>/<str:auction_name>/",
         views.htmx_company_years, name="htmx_company_years_with_auction"),
    path("api/auction-components/<str:company_id>/<str:year>/<str:auction_name>/",
         views.htmx_auction_components, name="htmx_auction_components"),
    path("api/cmu-details/<str:cmu_id>/",
         views.get_cmu_details, name="htmx_cmu_details"),

    # Component detail page - use integer primary key
    path("component/<int:pk>/",
         views.component_detail, name="component_detail"),
    path("component/by-id/<str:component_id>/",
         views.component_detail_by_id, name="component_detail_by_id"),
    
    # SEO-friendly component URLs
    path("components/<int:pk>/<slug:slug>/",
         views.component_detail, name="component_detail_seo"),

    # REMOVED: Old company detail page (replaced by optimized versions)
    # path("company/<str:company_id>/", views.company_detail, name="company_detail"),
    
    # REDIRECT: Company list view to map view (SEO canonical)
    path("company-list/<str:company_id>/",
         lambda request, company_id: redirect('company_detail_map', company_name=company_id, permanent=True)),
    
    
    # LEGACY: Keep old URL temporarily for backwards compatibility
    path("company-optimized/<str:company_id>/",
         lambda request, company_id: redirect('company_detail_optimized', company_id=company_id, permanent=True)),

    # CMU detail page
    path("cmu/<str:cmu_id>/",
         cmu_detail, name="cmu_detail"),
    
    # REDIRECT: CMU list view to map view (SEO canonical)
    path("cmu-optimized/<str:cmu_id>/",
         lambda request, cmu_id: redirect('cmu_detail_map', cmu_id=cmu_id, permanent=True)),

    # Map view and API
    path('map/', views.map_view, name='map_view'),
    path('map_search/', views.map_search_view, name='map_search_view'),
    path('search-map/', lambda request: redirect('search_map_view', permanent=True)),  # Backward compatibility redirect
    path('map-explorer/', map_explorer_view, name='map_explorer'),  # Mobile-optimized map explorer
    path('map_results/technology/', lambda request: redirect('map_view', permanent=True), name='technology_map_results'),
    path('map_results/company/', views.company_map_results_view, name='company_map_results'),
    path('map_results/', map_search_results_view, name='map_search_results'),
    path('map_test/', views.map_search_test, name='map_search_test'),
    # path('map_test_fix/', map_search_fixed_view, name='map_search_fixed_view'), 
    path('api/map-data/', views.map_data_api, name='map_data_api'),
    path('api/search-geojson/', search_results_geojson, name='search_results_geojson'),
    path('api/batch-geojson/', batch_geojson_api, name='batch_geojson_api'),
    path('api/stream-geojson/', optimized_geojson_stream, name='optimized_geojson_stream'),
    path('api/component-map-detail/<int:component_id>/', views.component_map_detail_api, name='component_map_detail_api'),
    path('api/subtypes/', get_filtered_subtypes, name='filtered_subtypes'),
    path('api/company-technologies/', get_company_technologies, name='company_technologies'),
    path('api/search-filters/', search_filters_api, name='search_filters_api'),

    # Location-based views
    path('location/<int:location_id>/', location_detail, name='location_detail'),
    path('location/by-name/<path:location_name>/', views.location_detail_by_name, name='location_detail_by_name'),
    
    # SEO-friendly location URLs
    path('locations/<int:pk>/<slug:slug>/', location_detail_by_name_seo, name='location_detail_seo'),
    # path('test/location-search/', test_location_search, name='test_location_search'),
    # path('test/location-search-html/', test_location_search_html, name='test_location_search_html'),
    # path('test/location-search-styled/', test_location_search_styled, name='test_location_search_styled'),
    
    # Unified search and map test views
    # path('test/unified-search-map/', unified_search_map_test, name='unified_search_map_test'),
    # path('test/unified-search-map-google/', unified_search_map_google_test, name='unified_search_map_google_test'),
    # path('test/google-maps/', test_google_maps, name='test_google_maps'),
    # path('test/search-with-map/', search_with_map, name='search_with_map'),
    # path('test/search-results-with-map/', search_results_with_map, name='search_results_with_map'),
    # path('test/search-results-with-map-real/', search_results_with_map_real, name='search_results_with_map_real'),
    # path('test/search-results-with-map-google/', search_results_with_map_google, name='search_results_with_map_google'),
    
    # Debug/admin endpoints
    path("debug/mapping-cache/",
         views.debug_mapping_cache, name="debug_mapping_cache"),

    # API endpoint for getting auction components (redundant with HTMX endpoint above)
    # path("api/auction-components/<str:company_id>/<str:year>/<str:auction_name>/", views.auction_components, name="auction_components_api"),
    
    # Debug endpoint for troubleshooting component issues
    path("debug/auction-components/<str:company_id>/<str:year>/<str:auction_name>/", views.debug_auction_components, name="debug_auction_components"),

    # Debug endpoints
    path("debug/cache/<str:cmu_id>/",
         views.debug_cache, name="debug_cache"),
#    path("debug/mapping/",
#         views.debug_mapping, name="debug_mapping"),
    path("debug/mapping-cache/",
         views.debug_mapping_cache, name="debug_mapping_cache"),
         
    # New debug endpoint for component investigation
    path("debug/component-retrieval/<str:cmu_id>/",
         views.debug_component_retrieval, name="debug_component_retrieval"),
         
    # Debug endpoint for company components
    path("debug/company-components/",
         views.debug_company_components, name="debug_company_components"),

    # Debug URLs
    path('debug/duplicates/<str:cmu_id>/', debug_component_duplicates, name='debug_duplicates'),
    # REMOVED: Statistics page caused massive Supabase egress (10-50MB per page load)
    
    # Index information endpoint
    path('debug/indexes/', views.index_info, name='index_info'),
    
    # Technology search - redirect to optimized version
    path('technology/<path:technology_name_encoded>/', lambda request, technology_name_encoded: redirect('technology_detail_map', technology_name=technology_name_encoded), name='technology_search'),
    
    # REDIRECT: Technology list view to map view (SEO canonical)
    path('technology-optimized/<path:technology_name>/', 
         lambda request, technology_name: redirect('technology_detail_map', technology_name=technology_name, permanent=True)),
    
    
    
    # Ultra-minimal SEO endpoints for search engine bots
    path('seo/search/', search_seo_minimal, name='search_seo_minimal'),
    path('seo/company/<path:company_name>/', company_seo_minimal, name='company_seo_minimal'),
    path('seo/technology/<path:technology_name>/', technology_seo_minimal, name='technology_seo_minimal'),
    path('seo/location/<str:location_group_id>/', location_seo_minimal, name='location_seo_minimal'),
    path('seo/component/<int:component_id>/', component_seo_minimal, name='component_seo_minimal'),
    path('seo/cmu/<str:cmu_id>/', cmu_seo_minimal, name='cmu_seo_minimal'),
    
    # NEW SEO-FRIENDLY URL STRUCTURE
    
    # Directory pages (must come before individual pages to avoid conflicts)
    path('companies/', company_list_optimized, name='company_list_optimized'),
    path('companies/by-total-capacity/', company_list_optimized, name='company_capacity_list'),
    path('companies/by-component-count/', company_list_optimized, name='company_component_count_list'),
    
    path('technologies/', technology_list_optimized, name='technology_list'),
    path('technologies/by-total-capacity/', technology_list_optimized, name='technology_capacity_list'),
    
    path('components/', lambda request: redirect('search_map_view'), name='component_list'),
    path('locations/', lambda request: redirect('search_map_view'), name='location_list'),
    path('cmus/', lambda request: redirect('search_map_view'), name='cmu_list'),
    
    # Individual pages (must come after directory pages) 
    # Accept both slugs and legacy URL-encoded names
    path('companies/<path:company_name>/', company_detail_map, name='company_detail_map'),
    path('technologies/<path:technology_name>/', technology_detail_map, name='technology_detail_map'),
    path('cmus/<str:cmu_id>/', cmu_detail_map, name='cmu_detail_map'),
    
    # Hierarchical structure: /locations/id/components/id
    path('locations/<int:location_id>/components/<int:pk>/', get_component_details, name='component_detail_hierarchical'),
    
    # Flat structure (backward compatibility)
    path('components/<int:pk>/', get_component_details, name='component_detail'),
    path('locations/<int:location_id>/', location_detail, name='location_detail'),
    
    # LEGACY URLs (will be redirected)
    path('company-map/<path:company_name>/', lambda request, company_name: redirect('company_detail_map', company_name=slugify(company_name), permanent=True)),
    path('technology-map/<path:technology_name>/', lambda request, technology_name: redirect('technology_detail_map', technology_name=slugify(technology_name), permanent=True)),
    path('cmu-map/<str:cmu_id>/', lambda request, cmu_id: redirect('cmu_detail_map', cmu_id=cmu_id, permanent=True)),

    # New URL for full de-rated capacity list (components)
    path('components/by-derated-capacity/', views.derated_capacity_list, name='derated_capacity_list'),

    
    # Market component lists
    path('components/current-market/', views.current_market_list, name='current_market_list'),
    path('components/past-market/', views.past_market_list, name='past_market_list'),

    # Legacy GPT API endpoint - serving JSON directly for AI compatibility
    path('api/gpt-search/', views.search_json_api_direct, name='gpt_search_api'),
    path('api/gpt-search-readme/', views.gpt_api_readme, name='gpt_api_readme'),
    
    # Health check endpoint that always returns JSON (never "OK")
    path('api/health/', views.api_health_view, name='api_health'),
    
    # JSON endpoints - serving directly for AI compatibility
    path('search-json/', views.search_json_api_direct, name='search_json_api'),
    path('search-map-json/', views.search_map_json_api_direct, name='search_map_json_api'),
    
    # Battery Storage Guide
    path('guides/battery-storage/', views.battery_storage_guide, name='battery_storage_guide'),
    
    # Capacity Market Guide
    path('guides/capacity-market/', views.capacity_market_guide, name='capacity_market_guide'),
    
    # Capacity Market FAQ
    path('guides/capacity-market-faq/', views.capacity_market_faq, name='capacity_market_faq'),
    
    # Secondary Trading Guide
    path('guides/secondary-trading/', views.secondary_trading_guide, name='secondary_trading_guide'),
    
    # RESTRICTED: Old search endpoints - access restricted
    path("search-optimized/", search_components_optimized, name="search_optimized"),
    path("search-optimized-v2/", search_components_optimized_v2, name="search_optimized_v2"),
    
    # MAIN SEARCH ROUTE - moved from /search-map/ for simplicity
    path("search/", search_map_view_simple, name="search_map_view"),
    
    # Root path shows homepage - UPDATED FOR HOMEPAGE FIX
    path("", homepage_view, name="homepage"),
    
    # RESTRICTED: Legacy search - access restricted
    path("search-legacy/", search_components_service, name="search_companies_legacy"),
    
    # Cache monitoring endpoints (staff only)
    path("cache-monitor/", cache_monitor_dashboard, name="cache_monitor_dashboard"),
    path("cache-monitor/api/", cache_monitor_api, name="cache_monitor_api"),
]