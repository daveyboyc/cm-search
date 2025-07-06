"""
Ultra-minimal SEO views for search engine bots
Serves lightweight responses with essential data only
"""
from django.http import HttpResponse
from django.db import connection
from django.utils.html import escape
from django.core.cache import cache
import json
import logging
import time
import urllib.parse

from .models import Component, LocationGroup
from .bot_detection import is_bot_request

logger = logging.getLogger(__name__)

def get_canonical_url(request):
    """Convert /seo/ URL to canonical main URL"""
    path = request.path
    if path.startswith('/seo/'):
        # Convert /seo/company/EDF/ to /company-map/EDF/
        if '/seo/company/' in path:
            company_name = path.replace('/seo/company/', '').rstrip('/')
            return f"{request.scheme}://{request.get_host()}/company-map/{company_name}/"
        elif '/seo/technology/' in path:
            tech_name = path.replace('/seo/technology/', '').rstrip('/')
            return f"{request.scheme}://{request.get_host()}/technology-map/{tech_name}/"
        elif '/seo/cmu/' in path:
            cmu_id = path.replace('/seo/cmu/', '').rstrip('/')
            return f"{request.scheme}://{request.get_host()}/cmu-map/{cmu_id}/"
        elif '/seo/component/' in path:
            component_id = path.replace('/seo/component/', '').rstrip('/')
            return f"{request.scheme}://{request.get_host()}/component/{component_id}/"
        elif '/seo/location/' in path:
            location_id = path.replace('/seo/location/', '').rstrip('/')
            return f"{request.scheme}://{request.get_host()}/location/{location_id}/"
        elif '/seo/search/' in path:
            return f"{request.scheme}://{request.get_host()}/search/"
    
    return request.build_absolute_uri()

def get_seo_response_type(request):
    """Enhanced bot detection for SEO endpoints"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Search engine bots get minimal SEO responses
    search_bots = ['googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider']
    for bot in search_bots:
        if bot in user_agent:
            return 'seo_minimal'
    
    # Social media bots get structured data
    social_bots = ['facebookexternalhit', 'twitterbot', 'linkedinbot']
    for bot in social_bots:
        if bot in user_agent:
            return 'social_minimal'
            
    return 'normal'

def create_minimal_seo_response(request, title, description, content_html, structured_data=None):
    """Generate ultra-minimal SEO response with no CSS/JS"""
    
    # Create structured data script tag if provided
    structured_data_tag = ""
    if structured_data:
        structured_data_tag = f'<script type="application/ld+json">{json.dumps(structured_data, indent=2)}</script>'
    
    # Generate minimal HTML (no CSS, no JS, no templates)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}">
    <link rel="canonical" href="{get_canonical_url(request)}">
    <meta property="og:title" content="{escape(title)}">
    <meta property="og:description" content="{escape(description)}">
    <meta property="og:url" content="{request.build_absolute_uri()}">
    <meta property="og:type" content="website">
    <meta name="robots" content="noindex,follow">
    {structured_data_tag}
</head>
<body>
    <h1>{escape(title)}</h1>
    <p>{escape(description)}</p>
    {content_html}
    <footer>
        <p>UK Capacity Market Data - Minimal SEO View</p>
    </footer>
</body>
</html>"""
    
    response = HttpResponse(html, content_type='text/html')
    response['X-Bot-Response'] = 'seo_minimal'
    response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
    
    # Debug logging for response size
    response_size = len(html.encode('utf-8'))
    logger.info(f"📦 SEO MINIMAL RESPONSE: {response_size:,} bytes ({response_size/1024:.1f} KB)")
    
    return response

def company_seo_minimal(request, company_name):
    """Ultra-minimal company view for search engines"""
    start_time = time.time()
    
    # Check if this should get minimal response
    response_type = get_seo_response_type(request)
    
    # Decode and normalize company name
    company_display = urllib.parse.unquote(company_name)
    
    # Check cache first
    cache_key = f"seo_company_{company_name.lower()}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"🚀 SEO CACHE HIT: {company_display}")
        return create_minimal_seo_response(request, **cached_data)
    
    # Minimal database query - only essential fields
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT location, technology, derated_capacity_mw, delivery_year
            FROM checker_component 
            WHERE company_name ILIKE %s 
            ORDER BY derated_capacity_mw DESC NULLS LAST
            LIMIT 10
        """, [f"%{company_display}%"])
        
        components = cursor.fetchall()
    
    if not components:
        # Return minimal 404-style response
        title = f"{company_display} - UK Capacity Market"
        description = f"No capacity market components found for {company_display}"
        content_html = f"<p>No components found for company: {escape(company_display)}</p>"
        
        response_data = {
            'title': title,
            'description': description,
            'content_html': content_html
        }
        cache.set(cache_key, response_data, 1800)  # Cache for 30 minutes
        return create_minimal_seo_response(request, **response_data)
    
    # Calculate totals
    total_capacity = sum(float(comp[2] or 0) for comp in components)
    unique_locations = len(set(comp[0] for comp in components if comp[0]))
    unique_technologies = set(comp[1] for comp in components if comp[1])
    
    # Build minimal content
    title = f"{company_display} - UK Capacity Market ({total_capacity:.1f} MW)"
    description = f"{company_display} operates {len(components)} capacity market components across {unique_locations} locations with {total_capacity:.1f} MW total capacity."
    
    # Create minimal content list
    content_html = f"""
    <h2>Summary</h2>
    <ul>
        <li><strong>Total Capacity:</strong> {total_capacity:.1f} MW</li>
        <li><strong>Components:</strong> {len(components)}</li>
        <li><strong>Locations:</strong> {unique_locations}</li>
        <li><strong>Technologies:</strong> {', '.join(sorted(unique_technologies))}</li>
    </ul>
    
    <h2>Components</h2>
    <ul>"""
    
    for comp in components:
        location, technology, capacity, delivery_year = comp
        capacity_str = f"{capacity:.1f} MW" if capacity else "Capacity not specified"
        year_str = f" ({delivery_year})" if delivery_year else ""
        content_html += f"""
        <li>{escape(location or 'Location not specified')} - {escape(technology or 'Technology not specified')} - {capacity_str}{year_str}</li>"""
    
    content_html += "</ul>"
    
    # Create structured data for search engines
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": company_display,
        "description": f"UK Capacity Market participant operating {total_capacity:.1f} MW of capacity",
        "location": {
            "@type": "Place",
            "addressCountry": "GB"
        },
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "numberOfItems": str(len(components)),
            "itemListElement": [
                {
                    "@type": "Offer",
                    "name": f"{comp[1] or 'Energy Storage'} at {comp[0] or 'UK Location'}",
                    "description": f"Capacity market component with {comp[2] or 0} MW capacity"
                } for comp in components[:5]  # Limit structured data to 5 items
            ]
        }
    }
    
    response_data = {
        'title': title,
        'description': description,
        'content_html': content_html,
        'structured_data': structured_data
    }
    
    # Cache the response data
    cache.set(cache_key, response_data, 3600)  # Cache for 1 hour
    
    # Log performance
    response_time = (time.time() - start_time) * 1000
    is_bot, bot_type = is_bot_request(request)
    logger.info(f"🤖 SEO MINIMAL: {bot_type or 'unknown'} -> /seo/company/{company_name} (time: {response_time:.1f}ms)")
    
    return create_minimal_seo_response(request, **response_data)

def technology_seo_minimal(request, technology_name):
    """Ultra-minimal technology view for search engines"""
    start_time = time.time()
    
    # Decode and normalize technology name
    technology_display = urllib.parse.unquote(technology_name).replace('_', ' ')
    
    # Check cache first
    cache_key = f"seo_technology_{technology_name.lower()}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"🚀 SEO CACHE HIT: {technology_display}")
        return create_minimal_seo_response(request, **cached_data)
    
    # Minimal database query
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT company_name, location, derated_capacity_mw, delivery_year
            FROM checker_component 
            WHERE technology ILIKE %s 
            ORDER BY derated_capacity_mw DESC NULLS LAST
            LIMIT 15
        """, [f"%{technology_display}%"])
        
        components = cursor.fetchall()
    
    if not components:
        title = f"{technology_display} - UK Capacity Market"
        description = f"No capacity market components found using {technology_display} technology"
        content_html = f"<p>No components found for technology: {escape(technology_display)}</p>"
        
        response_data = {
            'title': title,
            'description': description,
            'content_html': content_html
        }
        cache.set(cache_key, response_data, 1800)
        return create_minimal_seo_response(request, **response_data)
    
    # Calculate totals
    total_capacity = sum(float(comp[2] or 0) for comp in components)
    unique_companies = len(set(comp[0] for comp in components if comp[0]))
    unique_locations = len(set(comp[1] for comp in components if comp[1]))
    
    # Build minimal content
    title = f"{technology_display} - UK Capacity Market ({total_capacity:.1f} MW)"
    description = f"{len(components)} capacity market components using {technology_display} technology, totaling {total_capacity:.1f} MW across {unique_companies} companies."
    
    # Create minimal content
    content_html = f"""
    <h2>Summary</h2>
    <ul>
        <li><strong>Total Capacity:</strong> {total_capacity:.1f} MW</li>
        <li><strong>Components:</strong> {len(components)}</li>
        <li><strong>Companies:</strong> {unique_companies}</li>
        <li><strong>Locations:</strong> {unique_locations}</li>
    </ul>
    
    <h2>Components</h2>
    <ul>"""
    
    for comp in components:
        company, location, capacity, delivery_year = comp
        capacity_str = f"{capacity:.1f} MW" if capacity else "Capacity not specified"
        year_str = f" ({delivery_year})" if delivery_year else ""
        content_html += f"""
        <li>{escape(company or 'Company not specified')} - {escape(location or 'Location not specified')} - {capacity_str}{year_str}</li>"""
    
    content_html += "</ul>"
    
    # Structured data for technology
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{technology_display} - UK Capacity Market",
        "description": f"Capacity market components using {technology_display} technology",
        "keywords": f"UK, capacity market, {technology_display}, energy storage, power generation",
        "creator": {
            "@type": "Organization",
            "name": "UK Capacity Market Registry"
        },
        "distribution": {
            "@type": "DataDownload",
            "contentUrl": request.build_absolute_uri(),
            "encodingFormat": "text/html"
        }
    }
    
    response_data = {
        'title': title,
        'description': description,
        'content_html': content_html,
        'structured_data': structured_data
    }
    
    cache.set(cache_key, response_data, 3600)
    
    # Log performance
    response_time = (time.time() - start_time) * 1000
    is_bot, bot_type = is_bot_request(request)
    logger.info(f"🤖 SEO MINIMAL: {bot_type or 'unknown'} -> /seo/technology/{technology_name} (time: {response_time:.1f}ms)")
    
    return create_minimal_seo_response(request, **response_data)

def location_seo_minimal(request, location_group_id):
    """Ultra-minimal location view for search engines"""
    start_time = time.time()
    
    # Check cache first
    cache_key = f"seo_location_{location_group_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"🚀 SEO CACHE HIT: location {location_group_id}")
        return create_minimal_seo_response(request, **cached_data)
    
    # Get location data
    try:
        location_group = LocationGroup.objects.get(id=location_group_id)
    except LocationGroup.DoesNotExist:
        title = "Location Not Found - UK Capacity Market"
        description = "The requested location was not found in the UK Capacity Market database"
        content_html = "<p>Location not found.</p>"
        
        response_data = {
            'title': title,
            'description': description,
            'content_html': content_html
        }
        return create_minimal_seo_response(request, **response_data)
    
    # Extract primary data
    location = location_group.location
    total_capacity = location_group.normalized_capacity_mw or 0
    companies = location_group.companies or {}
    technologies = location_group.technologies or {}
    component_count = location_group.component_count or 0
    
    # Build minimal content
    title = f"{location} - UK Capacity Market ({total_capacity:.1f} MW)"
    description = f"{component_count} capacity market components at {location} with {total_capacity:.1f} MW total capacity"
    
    # Create content
    content_html = f"""
    <h2>Summary</h2>
    <ul>
        <li><strong>Location:</strong> {escape(location)}</li>
        <li><strong>Total Capacity:</strong> {total_capacity:.1f} MW</li>
        <li><strong>Components:</strong> {component_count}</li>
        <li><strong>Companies:</strong> {len(companies)}</li>
        <li><strong>Technologies:</strong> {', '.join(sorted(technologies.keys()))}</li>
    </ul>
    
    <h2>Major Companies</h2>
    <ul>"""
    
    for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]:
        content_html += f"""
        <li>{escape(company)} ({count} components)</li>"""
    
    content_html += "</ul>"
    
    # Structured data for location
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Place",
        "name": location,
        "description": f"UK Capacity Market location with {component_count} components",
        "geo": {
            "@type": "GeoCoordinates",
            "addressCountry": "GB"
        }
    }
    
    response_data = {
        'title': title,
        'description': description,
        'content_html': content_html,
        'structured_data': structured_data
    }
    
    cache.set(cache_key, response_data, 3600)
    
    # Log performance
    response_time = (time.time() - start_time) * 1000
    is_bot, bot_type = is_bot_request(request)
    logger.info(f"🤖 SEO MINIMAL: {bot_type or 'unknown'} -> /seo/location/{location_group_id} (time: {response_time:.1f}ms)")
    
    return create_minimal_seo_response(request, **response_data)

def component_seo_minimal(request, component_id):
    """Ultra-minimal component view for search engines"""
    start_time = time.time()
    
    # Check cache
    cache_key = f"seo_component_{component_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"🚀 SEO CACHE HIT: component {component_id}")
        return create_minimal_seo_response(request, **cached_data)
    
    # Get component data by database ID (pk)
    try:
        component_obj = Component.objects.get(pk=component_id)
        component = (
            component_obj.cmu_id,
            component_obj.company_name,
            component_obj.technology,
            component_obj.location,
            component_obj.derated_capacity_mw,
            component_obj.delivery_year,
            component_obj.auction_name
        )
    except Component.DoesNotExist:
        component = None
    
    if not component:
        title = "Component Not Found - UK Capacity Market"
        description = "The requested component was not found in the UK Capacity Market database"
        content_html = "<p>Component not found.</p>"
        
        response_data = {
            'title': title,
            'description': description,
            'content_html': content_html
        }
        return create_minimal_seo_response(request, **response_data)
    
    # Extract data
    cmu_id, company, technology, location, capacity, delivery_year, auction = component
    capacity_str = f"{capacity:.1f} MW" if capacity else "Capacity not specified"
    
    # Build content
    title = f"{cmu_id} - {company or 'Unknown Company'} - UK Capacity Market"
    description = f"{technology or 'Energy storage'} component at {location or 'UK location'} with {capacity_str} capacity"
    
    content_html = f"""
    <h2>Component Details</h2>
    <ul>
        <li><strong>CMU ID:</strong> {escape(cmu_id)}</li>
        <li><strong>Company:</strong> {escape(company or 'Not specified')}</li>
        <li><strong>Technology:</strong> {escape(technology or 'Not specified')}</li>
        <li><strong>Location:</strong> {escape(location or 'Not specified')}</li>
        <li><strong>Capacity:</strong> {capacity_str}</li>
        <li><strong>Delivery Year:</strong> {escape(delivery_year or 'Not specified')}</li>
        <li><strong>Auction:</strong> {escape(auction or 'Not specified')}</li>
    </ul>
    """
    
    # Structured data
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{cmu_id} - {technology or 'Energy Storage'}",
        "description": description,
        "manufacturer": {
            "@type": "Organization",
            "name": company or "Unknown"
        },
        "model": cmu_id
    }
    
    response_data = {
        'title': title,
        'description': description,
        'content_html': content_html,
        'structured_data': structured_data
    }
    
    cache.set(cache_key, response_data, 3600)
    
    # Log performance
    response_time = (time.time() - start_time) * 1000
    is_bot, bot_type = is_bot_request(request)
    logger.info(f"🤖 SEO MINIMAL: {bot_type or 'unknown'} -> /seo/component/{component_id} (time: {response_time:.1f}ms)")
    
    return create_minimal_seo_response(request, **response_data)

def search_seo_minimal(request):
    """Ultra-minimal search results for search engines"""
    start_time = time.time()
    query = request.GET.get('q', '').strip()
    
    if not query:
        title = "Search - UK Capacity Market"
        description = "Search the UK Capacity Market database for components, companies, technologies and locations"
        content_html = "<p>Enter a search term to find capacity market data.</p>"
        
        return create_minimal_seo_response(request, title, description, content_html)
    
    # Check cache
    cache_key = f"seo_search_{query.lower()}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"🚀 SEO CACHE HIT: search '{query}'")
        return create_minimal_seo_response(request, **cached_data)
    
    # Search for components
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT company_name, technology, location, derated_capacity_mw, delivery_year
            FROM checker_component 
            WHERE company_name ILIKE %s 
               OR technology ILIKE %s 
               OR location ILIKE %s
               OR cmu_id ILIKE %s
            ORDER BY derated_capacity_mw DESC NULLS LAST
            LIMIT 20
        """, [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
        
        results = cursor.fetchall()
    
    if not results:
        title = f"'{query}' - No Results - UK Capacity Market"
        description = f"No capacity market components found matching '{query}'"
        content_html = f"<p>No results found for '{escape(query)}'.</p>"
        
        response_data = {
            'title': title,
            'description': description,
            'content_html': content_html
        }
        cache.set(cache_key, response_data, 1800)
        return create_minimal_seo_response(request, **response_data)
    
    # Build results
    title = f"'{query}' - UK Capacity Market Search Results"
    description = f"Found {len(results)} capacity market components matching '{query}'"
    
    content_html = f"""
    <h1>Search Results for "{escape(query)}"</h1>
    <p>Found {len(results)} matching components</p>
    
    <h2>Results</h2>
    <ul>"""
    
    for result in results:
        company, technology, location, capacity, delivery_year = result
        capacity_str = f"{capacity:.1f} MW" if capacity else "N/A"
        year_str = f" ({delivery_year})" if delivery_year else ""
        
        content_html += f"""
        <li>
            <strong>{escape(company or 'Unknown Company')}</strong> - 
            {escape(location or 'Unknown Location')} - 
            {escape(technology or 'Unknown Technology')} - 
            {capacity_str}{year_str}
        </li>"""
    
    content_html += "</ul>"
    
    # Structured data for search results
    structured_data = {
        "@context": "https://schema.org",
        "@type": "SearchResultsPage",
        "name": title,
        "description": description,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(results),
            "itemListElement": []
        }
    }
    
    response_data = {
        'title': title,
        'description': description,
        'content_html': content_html,
        'structured_data': structured_data
    }
    
    cache.set(cache_key, response_data, 3600)
    
    # Log performance
    response_time = (time.time() - start_time) * 1000
    is_bot, bot_type = is_bot_request(request)
    logger.info(f"🤖 SEO MINIMAL: {bot_type or 'unknown'} -> /seo/search/?q={query} (time: {response_time:.1f}ms)")
    
    return create_minimal_seo_response(request, **response_data)

def cmu_seo_minimal(request, cmu_id):
    """Ultra-minimal CMU view for search engines"""
    start_time = time.time()
    
    # Check cache
    cache_key = f"seo_cmu_{cmu_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"🚀 SEO CACHE HIT: CMU {cmu_id}")
        return create_minimal_seo_response(request, **cached_data)
    
    # Get CMU data
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cmu_id, company_name, technology, location, 
                   derated_capacity_mw, delivery_year, auction_name
            FROM checker_component 
            WHERE cmu_id = %s
            LIMIT 1
        """, [cmu_id])
        
        component = cursor.fetchone()
    
    if not component:
        title = f"CMU {cmu_id} - Not Found - UK Capacity Market"
        description = f"CMU {cmu_id} was not found in the UK Capacity Market database"
        content_html = f"<p>CMU {escape(cmu_id)} not found.</p>"
        
        response_data = {
            'title': title,
            'description': description,
            'content_html': content_html
        }
        cache.set(cache_key, response_data, 1800)
        return create_minimal_seo_response(request, **response_data)
    
    # Extract data
    cmu_id_db, company, technology, location, capacity, delivery_year, auction = component
    capacity_str = f"{capacity:.1f} MW" if capacity else "Capacity not specified"
    
    # Build content
    title = f"CMU {cmu_id} - {company or 'Unknown Company'} - UK Capacity Market"
    description = f"Capacity Market Unit {cmu_id}: {technology or 'Energy storage'} at {location or 'UK location'} with {capacity_str}"
    
    content_html = f"""
    <h2>Capacity Market Unit Details</h2>
    <ul>
        <li><strong>CMU ID:</strong> {escape(cmu_id)}</li>
        <li><strong>Company:</strong> {escape(company or 'Not specified')}</li>
        <li><strong>Technology:</strong> {escape(technology or 'Not specified')}</li>
        <li><strong>Location:</strong> {escape(location or 'Not specified')}</li>
        <li><strong>Capacity:</strong> {capacity_str}</li>
        <li><strong>Delivery Year:</strong> {escape(delivery_year or 'Not specified')}</li>
        <li><strong>Auction:</strong> {escape(auction or 'Not specified')}</li>
    </ul>
    """
    
    # Structured data
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"CMU {cmu_id} - {technology or 'Energy Storage'}",
        "description": description,
        "manufacturer": {
            "@type": "Organization",
            "name": company or "Unknown"
        },
        "model": cmu_id,
        "identifier": cmu_id
    }
    
    response_data = {
        'title': title,
        'description': description,
        'content_html': content_html,
        'structured_data': structured_data
    }
    
    cache.set(cache_key, response_data, 3600)
    
    # Log performance
    response_time = (time.time() - start_time) * 1000
    is_bot, bot_type = is_bot_request(request)
    logger.info(f"🤖 SEO MINIMAL: {bot_type or 'unknown'} -> /seo/cmu/{cmu_id} (time: {response_time:.1f}ms)")
    
    return create_minimal_seo_response(request, **response_data)