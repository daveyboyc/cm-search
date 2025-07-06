"""
SEO-friendly URL views that handle slug-based routing
"""
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.utils.text import slugify
from .models import LocationGroup, Component
from .views_location_detail import location_detail
from .views_company_optimized import company_detail_optimized
from .views_technology_optimized import technology_detail_optimized
from . import views
import urllib.parse

def location_detail_by_name_seo(request, pk, slug):
    """
    Handle SEO-friendly location URLs like /locations/123/some-location-name-np234sl/
    """
    try:
        location_group = get_object_or_404(LocationGroup, pk=pk)
        
        # Check if the slug matches (for canonical URLs)
        expected_slug = location_group.slug or slugify(location_group.location)[:300]
        if slug != expected_slug:
            # 301 redirect to canonical URL
            return redirect('location_detail_seo', pk=pk, slug=expected_slug, permanent=True)
        
        # Use the existing location detail view by name
        return views.location_detail_by_name(request, location_group.location)
        
    except LocationGroup.DoesNotExist:
        raise Http404("Location not found")

def company_detail_seo(request, slug):
    """
    Handle SEO-friendly company URLs like /companies/some-company-name/
    """
    # Convert slug back to company name
    company_name = slug.replace('-', ' ').title()
    
    # Try to find a matching company in the database
    # This is a simple approach - you might want more sophisticated matching
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT jsonb_object_keys(companies::jsonb) AS company
            FROM checker_locationgroup 
            WHERE companies IS NOT NULL
        """)
        companies = [row[0] for row in cursor.fetchall()]
    
    # Find best match (exact or close)
    matched_company = None
    for company in companies:
        if slugify(company) == slug:
            matched_company = company
            break
        elif company.upper() == company_name.upper():
            matched_company = company
            break
    
    if not matched_company:
        raise Http404("Company not found")
    
    # Redirect to canonical URL if slug doesn't match exactly
    canonical_slug = slugify(matched_company)
    if slug != canonical_slug:
        return redirect('company_detail_seo', slug=canonical_slug, permanent=True)
    
    # Use the existing company detail view
    return company_detail_optimized(request, matched_company)

def technology_detail_seo(request, slug):
    """
    Handle SEO-friendly technology URLs like /technologies/battery-storage/
    """
    # Convert slug back to technology name
    technology_name = slug.replace('-', ' ').title()
    
    # Try to find a matching technology in the database
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT jsonb_object_keys(technologies::jsonb) AS tech
            FROM checker_locationgroup 
            WHERE technologies IS NOT NULL
        """)
        technologies = [row[0] for row in cursor.fetchall()]
    
    # Find best match (exact or close)
    matched_technology = None
    for tech in technologies:
        if slugify(tech) == slug:
            matched_technology = tech
            break
        elif tech.upper() == technology_name.upper():
            matched_technology = tech
            break
    
    if not matched_technology:
        raise Http404("Technology not found")
    
    # Redirect to canonical URL if slug doesn't match exactly
    canonical_slug = slugify(matched_technology)
    if slug != canonical_slug:
        return redirect('technology_detail_seo', slug=canonical_slug, permanent=True)
    
    # Use the existing technology detail view
    return technology_detail_optimized(request, matched_technology)