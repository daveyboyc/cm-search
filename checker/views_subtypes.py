"""
Server-side API for filtered subcategory data
Provides database-level filtering to show only relevant storage subcategories
"""
import json
import logging
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from .models import Component, LocationGroup

logger = logging.getLogger(__name__)

# @cache_page(60 * 30)  # Disabled to prevent Redis memory issues - API is fast enough without cache
@gzip_page
def get_filtered_subtypes(request):
    """
    Return only subtypes that have data for the given company and period
    Uses LocationGroup.is_active for database-level filtering like main technology filtering
    """
    try:
        # Get parameters from request
        category = request.GET.get('category', '')
        company = request.GET.get('company', '')
        cm_period = request.GET.get('period', 'future')
        
        logger.info(f"📡 API call: category={category}, company={company}, period={cm_period}")
        
        # Map period to is_active field (matching main technology filtering)
        if cm_period in ['future', 'active']:
            # Active = future period, filter by is_active=True
            active_locations = LocationGroup.objects.filter(is_active=True).values_list('location', flat=True)
            base_query = Component.objects.filter(location__in=active_locations)
        else:
            # Inactive = historical period, filter by is_active=False  
            inactive_locations = LocationGroup.objects.filter(is_active=False).values_list('location', flat=True)
            base_query = Component.objects.filter(location__in=inactive_locations)
        
        # Add company filter if specified
        if company and company.strip():
            base_query = base_query.filter(company_name=company.strip())
            logger.info(f"🏢 Filtering by company: {company}")
        
        # For Battery category, get all storage-related technologies
        if category == 'Battery':
            # Get all unique technology names that are specifically battery/storage related
            # Exclude DSR and other non-battery technologies
            storage_technologies = base_query.filter(
                (Q(technology__icontains='Storage') | Q(technology__icontains='Battery')) &
                ~Q(technology__icontains='DSR') &
                ~Q(technology__icontains='Demand Side Response') &
                ~Q(technology__icontains='CHP') &
                ~Q(technology__icontains='Gas') &
                ~Q(technology__icontains='Solar') &
                ~Q(technology__icontains='Wind')
            ).values_list('technology', flat=True).distinct().order_by('technology')
            
            subtypes = list(storage_technologies)
            logger.info(f"🔋 Found {len(subtypes)} battery storage subtypes: {subtypes}")
            
        elif category in ['Gas', 'OCGT']:
            # Get all gas-related technologies including reciprocating engines
            gas_technologies = base_query.filter(
                Q(technology__icontains='Gas') |
                Q(technology__icontains='CCGT') |
                Q(technology__icontains='OCGT') |
                Q(technology__icontains='SCGT') |
                Q(technology__icontains='Reciprocating engines') |
                Q(technology__icontains='reciprocating')
            ).values_list('technology', flat=True).distinct().order_by('technology')
            
            subtypes = list(gas_technologies)
            logger.info(f"🔥 Found {len(subtypes)} gas subtypes for category '{category}': {subtypes}")
            
        elif category == 'Interconnector':
            # Get all interconnector technologies - specific country connections
            interconnector_keywords = [
                'BritNED', 'EWIC', 'Eleclink', 'Greenlink', 'IFA', 'IFA2', 
                'Moyle', 'NEMO', 'NSL', 'NeuConnect', 'VikingLink',
                'Netherlands', 'Ireland', 'France', 'Belgium', 'Norway', 
                'Denmark', 'Germany', 'Northern Ireland', 'Republic of Ireland'
            ]
            
            # Build query for interconnector technologies
            interconnector_query = Q()
            for keyword in interconnector_keywords:
                interconnector_query |= Q(technology__icontains=keyword)
            
            # Also include any technology containing "interconnector" or "interconnection"
            interconnector_query |= Q(technology__icontains='interconnector')
            interconnector_query |= Q(technology__icontains='interconnection')
            
            interconnector_technologies = base_query.filter(
                interconnector_query
            ).values_list('technology', flat=True).distinct().order_by('technology')
            
            subtypes = list(interconnector_technologies)
            logger.info(f"🔗 Found {len(subtypes)} interconnector subtypes: {subtypes}")
            
        elif category == 'DSR':
            # If a specific company is selected, no subtypes needed for DSR
            if company and company.strip():
                subtypes = []
                logger.info(f"⚡ DSR with company '{company}' selected - no subtypes needed")
            else:
                # DSR shows 3 hardcoded subtypes: Octopus, Axle, Everything else
                subtypes = ['Octopus', 'Axle', 'Everything else']
                logger.info(f"⚡ Found {len(subtypes)} DSR subtypes: {subtypes}")
            
        elif category == 'EV Charging':
            # EV Charging shows company names as subtypes instead of technology variations
            if cm_period in ['future', 'active']:
                location_groups = LocationGroup.objects.filter(is_active=True)
            else:
                location_groups = LocationGroup.objects.filter(is_active=False)
            
            # Filter for EV Charging technology
            location_groups = location_groups.filter(technologies__has_key='EV Charging')
            
            # If a specific company is selected, no subtypes needed for EV Charging
            if company and company.strip():
                subtypes = []
                logger.info(f"🔌 EV Charging with company '{company}' selected - no subtypes needed")
            else:
                # No company filter - check if Octopus/Axle have EV Charging, then add other companies
                subtypes = []
                
                # Check if Octopus has EV Charging locations in current period
                if location_groups.filter(companies__has_key='OCTOPUS ENERGY LIMITED').exists():
                    subtypes.append('Octopus')
                
                # Check if Axle has EV Charging locations in current period
                if location_groups.filter(companies__has_key='AXLE ENERGY LIMITED').exists():
                    subtypes.append('Axle')
                
                # Find other companies that have EV Charging technology
                ev_companies = {}
                for lg in location_groups:
                    if lg.companies:
                        companies = lg.companies if isinstance(lg.companies, dict) else json.loads(lg.companies)
                        for company_name, count in companies.items():
                            # Exclude residential DSR companies from the "other" list
                            if company_name not in ['AXLE ENERGY LIMITED', 'OCTOPUS ENERGY LIMITED']:
                                ev_companies[company_name] = ev_companies.get(company_name, 0) + count
                
                # Sort by count and take top companies to fill remaining slots
                sorted_companies = sorted(ev_companies.items(), key=lambda x: x[1], reverse=True)
                # Take enough to make ~11 total items
                remaining_slots = 10 - len(subtypes)  # Leave room for "Everything else"
                subtypes.extend([company[0] for company in sorted_companies[:remaining_slots]])
                
                # Add "Everything else" option at the end
                subtypes.append('Everything else')
                
                logger.info(f"🔌 Building EV Charging subtypes - Initial: {subtypes[:2]}, Companies: {len(sorted_companies)}, Total: {len(subtypes)}")
                logger.info(f"🔌 Full subtypes list: {subtypes}")
            
        else:
            # For other categories, get technologies that start with or contain the category name
            other_technologies = base_query.filter(
                Q(technology__icontains=category)
            ).values_list('technology', flat=True).distinct().order_by('technology')
            
            subtypes = list(other_technologies)
            logger.info(f"⚡ Found {len(subtypes)} {category} subtypes: {subtypes}")
        
        logger.info(f"✅ Returning {len(subtypes)} filtered subtypes for {category}")
        
        return JsonResponse({
            'subtypes': subtypes,
            'category': category,
            'company': company,
            'period': cm_period,
            'count': len(subtypes)
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_filtered_subtypes: {e}")
        return JsonResponse({
            'error': str(e),
            'subtypes': [],
            'category': category,
            'company': company,
            'period': cm_period,
            'count': 0
        }, status=500)