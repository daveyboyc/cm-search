"""
Structured data (JSON-LD) generation for SEO optimization
"""
import json
from datetime import datetime
from django.conf import settings


def generate_component_structured_data(component_detail, request):
    """
    Generate JSON-LD structured data for a component detail page
    """
    try:
        # Basic component information
        component_data = {
            "@context": "https://schema.org",
            "@type": "EnergyInfrastructure", 
            "name": f"{component_detail.get('Description', 'UK Capacity Market Component')}",
            "description": f"Capacity market component with {component_detail.get('De-Rated Capacity (MW)', 'Unknown')} MW capacity",
            "url": request.build_absolute_uri(),
            "identifier": component_detail.get('CMU ID', ''),
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk",
                "description": "Official UK capacity market registry and database"
            }
        }
        
        # Add location if available
        location = component_detail.get('Location and Post Code')
        if location:
            component_data["location"] = {
                "@type": "Place",
                "name": location,
                "address": {
                    "@type": "PostalAddress",
                    "addressCountry": "GB",
                    "addressRegion": "UK"
                }
            }
        
        # Add organization/company if available
        company = component_detail.get('Company')
        if company:
            component_data["provider"] = {
                "@type": "Organization",
                "name": company,
                "address": {
                    "@type": "PostalAddress",
                    "addressCountry": "GB"
                }
            }
        
        # Add technical specifications
        capacity = component_detail.get('De-Rated Capacity (MW)')
        if capacity:
            try:
                capacity_value = float(capacity)
                component_data["technicalSpecification"] = {
                    "@type": "PropertyValue",
                    "name": "De-Rated Capacity",
                    "value": capacity_value,
                    "unitCode": "MW"
                }
            except (ValueError, TypeError):
                pass
        
        # Add delivery year if available
        delivery_year = component_detail.get('Delivery Year')
        if delivery_year:
            component_data["dateCreated"] = str(delivery_year)
        
        # Add technology type
        technology = component_detail.get('Technology')
        if technology:
            component_data["category"] = technology
        
        return json.dumps(component_data, indent=2)
    
    except Exception as e:
        # Return minimal data if there's an error
        return json.dumps({
            "@context": "https://schema.org",
            "@type": "EnergyInfrastructure",
            "name": "UK Capacity Market Component",
            "url": request.build_absolute_uri(),
            "creator": {
                "@type": "Organization", 
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk"
            }
        })


def generate_location_structured_data(location_group, organized_data, request):
    """
    Generate JSON-LD structured data for a location detail page
    """
    try:
        location_data = {
            "@context": "https://schema.org",
            "@type": "Place",
            "name": location_group.location,
            "description": f"Capacity market location with {location_group.component_count} components generating {location_group.get_display_capacity()}",
            "url": request.build_absolute_uri(),
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "GB",
                "addressRegion": "UK"
            },
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database", 
                "url": "https://capacitymarket.co.uk"
            }
        }
        
        # Add coordinates if available
        if location_group.latitude and location_group.longitude:
            location_data["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": float(location_group.latitude),
                "longitude": float(location_group.longitude)
            }
        
        # Add capacity information
        if hasattr(location_group, 'displayed_capacity_mw') and location_group.displayed_capacity_mw:
            location_data["additionalProperty"] = {
                "@type": "PropertyValue",
                "name": "Total Capacity",
                "value": location_group.displayed_capacity_mw,
                "unitCode": "MW"
            }
        
        # Add contained components
        if organized_data:
            components = []
            for description, cmu_dict in organized_data.items():
                for cmu_id, cmu_data in cmu_dict.items():
                    component = {
                        "@type": "EnergyInfrastructure",
                        "name": description or "Capacity Market Component",
                        "identifier": cmu_id,
                        "category": cmu_data.get('technology', 'Unknown')
                    }
                    
                    if cmu_data.get('company'):
                        component["provider"] = {
                            "@type": "Organization",
                            "name": cmu_data['company']
                        }
                    
                    components.append(component)
            
            if components:
                location_data["containsPlace"] = components[:10]  # Limit to 10 for performance
        
        return json.dumps(location_data, indent=2)
    
    except Exception as e:
        # Return minimal data if there's an error
        return json.dumps({
            "@context": "https://schema.org",
            "@type": "Place",
            "name": getattr(location_group, 'location', 'UK Capacity Market Location'),
            "url": request.build_absolute_uri(),
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk"
            }
        })


def generate_company_structured_data(company_name, company_data, request):
    """
    Generate JSON-LD structured data for a company detail page
    """
    try:
        company_structured = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": company_name,
            "description": f"UK Capacity Market participant with energy infrastructure assets",
            "url": request.build_absolute_uri(),
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "GB"
            },
            "industry": "Energy",
            "areaServed": {
                "@type": "Country",
                "name": "United Kingdom"
            },
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk" 
            }
        }
        
        # Add aggregated capacity if available
        if company_data and hasattr(company_data, 'total_capacity'):
            company_structured["additionalProperty"] = {
                "@type": "PropertyValue",
                "name": "Total Capacity",
                "value": company_data.total_capacity,
                "unitCode": "MW"
            }
        
        return json.dumps(company_structured, indent=2)
    
    except Exception as e:
        return json.dumps({
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": company_name,
            "url": request.build_absolute_uri(),
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk"
            }
        })


def generate_technology_structured_data(technology_name, technology_data, request):
    """
    Generate JSON-LD structured data for a technology detail page
    """
    try:
        technology_structured = {
            "@context": "https://schema.org",
            "@type": "TechnologyCategory",
            "name": f"{technology_name} Technology",
            "description": f"UK Capacity Market {technology_name} technology components and infrastructure",
            "url": request.build_absolute_uri(),
            "category": "Energy Technology",
            "areaServed": {
                "@type": "Country",
                "name": "United Kingdom"
            },
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk"
            }
        }
        
        return json.dumps(technology_structured, indent=2)
    
    except Exception as e:
        return json.dumps({
            "@context": "https://schema.org",
            "@type": "TechnologyCategory",
            "name": f"{technology_name} Technology",
            "url": request.build_absolute_uri(),
            "creator": {
                "@type": "Organization",
                "name": "UK Capacity Market Database",
                "url": "https://capacitymarket.co.uk"
            }
        })