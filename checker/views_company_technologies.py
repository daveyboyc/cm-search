"""
Optimized API endpoint for getting all available technologies for a company
Replaces multiple sequential API calls with a single efficient query
"""
import json
import logging
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from .models import LocationGroup

logger = logging.getLogger(__name__)

@cache_page(60 * 10)  # 10 minute cache
@gzip_page
def get_company_technologies(request):
    """
    Return all available technologies for a company in a single query
    Much faster than checking each technology category individually
    """
    try:
        # Get parameters
        company = request.GET.get('company', '')
        period = request.GET.get('period', 'active')
        
        logger.info(f"📡 Company technologies API: company={company}, period={period}")
        
        # Determine active/inactive filter
        if period in ['future', 'active']:
            location_groups = LocationGroup.objects.filter(is_active=True)
        else:
            location_groups = LocationGroup.objects.filter(is_active=False)
        
        # If no company selected or "Everything else", return all available technologies
        if not company or company.strip() == '' or company == 'Everything else':
            # Get all technologies across all location groups
            all_technologies = set()
            for lg in location_groups:
                if lg.technologies:
                    all_technologies.update(lg.technologies.keys())
            
            technologies = sorted(list(all_technologies))
            logger.info(f"✅ No company filter - returning {len(technologies)} technologies")
            
            return JsonResponse({
                'technologies': technologies,
                'company': company,
                'period': period,
                'count': len(technologies)
            })
        
        # Special case: Axle or Octopus - restrict to DSR and EV Charging only
        if company in ['AXLE ENERGY LIMITED', 'OCTOPUS ENERGY LIMITED']:
            restricted_techs = []
            
            # Check if they have DSR
            if location_groups.filter(companies__has_key=company, technologies__has_key='DSR').exists():
                restricted_techs.append('DSR')
            
            # Check if they have EV Charging
            if location_groups.filter(companies__has_key=company, technologies__has_key='EV Charging').exists():
                restricted_techs.append('EV Charging')
            
            logger.info(f"✅ {company} restricted to: {restricted_techs}")
            
            return JsonResponse({
                'technologies': restricted_techs,
                'company': company,
                'period': period,
                'count': len(restricted_techs)
            })
        
        # Regular company - get all their technologies in one query
        company_locations = location_groups.filter(companies__has_key=company)
        
        # Collect all unique technologies for this company
        company_technologies = set()
        for lg in company_locations:
            if lg.technologies:
                company_technologies.update(lg.technologies.keys())
        
        technologies = sorted(list(company_technologies))
        logger.info(f"✅ {company} has {len(technologies)} technologies: {technologies}")
        
        return JsonResponse({
            'technologies': technologies,
            'company': company,
            'period': period,
            'count': len(technologies)
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_company_technologies: {e}")
        return JsonResponse({
            'error': str(e),
            'technologies': [],
            'company': company,
            'period': period,
            'count': 0
        }, status=500)