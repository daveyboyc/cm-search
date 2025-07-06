from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.text import slugify
from django.urls import reverse
from django.contrib.postgres.search import SearchVectorField
import re

# Import Company model for PostgreSQL-based company search
from .models_company import Company

# Create your models here.

class Component(models.Model):
    """
    Model for storing components data
    """
    component_id = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    cmu_id = models.CharField(max_length=50, db_index=True)  # Already indexed
    location = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # Already indexed
    description = models.TextField(null=True, blank=True, db_index=True)  # Added index for description searches
    technology = models.CharField(max_length=100, db_index=True, null=True, blank=True)  # Already indexed
    company_name = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # Already indexed
    auction_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)  # Added index
    delivery_year = models.CharField(max_length=50, db_index=True, null=True, blank=True)  # Already indexed
    status = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    additional_data = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    # New field for numeric de-rated capacity
    derated_capacity_mw = models.FloatField(null=True, blank=True, db_index=True) 
    
    # Add these new fields for maps
    latitude = models.FloatField(null=True, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    geocoded = models.BooleanField(default=False)  # Track which records have been processed
    
    # Fields for location searching
    county = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    outward_code = models.CharField(max_length=5, null=True, blank=True, db_index=True)
    full_postcode = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    
    # Fields for Google Places API business detection
    places_api_business_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    places_api_confidence = models.FloatField(null=True, blank=True)  # 0.0 to 1.0 confidence score
    places_api_business_type = models.CharField(max_length=100, null=True, blank=True, db_index=True)  # e.g., supermarket, route, intersection
    places_api_search_strategy = models.CharField(max_length=50, null=True, blank=True)  # e.g., asda_specific, full_address
    places_api_major_retailers = models.JSONField(default=list, blank=True)  # List of major retailers found at location
    places_api_last_checked = models.DateTimeField(null=True, blank=True)
    
    # SEO-friendly slug (commented out until migration is run)
    # slug = models.SlugField(max_length=300, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Add compound indexes for common search patterns
        indexes = [
            # Compound index for company search with delivery year (common pattern)
            models.Index(fields=['company_name', 'delivery_year'], name='comp_delivery_idx'),
            
            # Compound index for location-based searches
            models.Index(fields=['location', 'company_name'], name='loc_comp_idx'),
            
            # Compound index for auction searches
            models.Index(fields=['auction_name', 'delivery_year'], name='auction_year_idx'),
            
            # Special index for 'vital' search (company_name LIKE 'VITAL ENERGI%' AND location NOT LIKE '%Leeds%')
            # This partial index would be ideal but requires PostgreSQL, 
            # so we'll create a regular compound index instead
            models.Index(fields=['company_name', 'location'], name='vital_search_idx'),
            
            # Add spatial index for map viewport queries
            models.Index(fields=['latitude', 'longitude'], name='spatial_idx'),
            
            # New composite index for technology and company_name
            models.Index(fields=['technology', 'company_name'], name='tech_comp_idx'),

            # New composite index for delivery_year and location
            models.Index(fields=['delivery_year', 'location'], name='year_loc_idx'),
        ]
        
        # Add database optimizations
        ordering = ['-delivery_year']  # Default ordering

    def __str__(self):
        return f"{self.cmu_id} - {self.component_id} ({self.location[:30]})"
    
    # def save(self, *args, **kwargs):
    #     if not self.slug:
    #         # Create slug from location, technology, and CMU ID
    #         slug_parts = []
    #         if self.location:
    #             slug_parts.append(self.location)
    #         if self.technology:
    #             slug_parts.append(self.technology)
    #         if self.cmu_id:
    #             slug_parts.append(f"cmu-{self.cmu_id}")
    #         
    #         slug_text = "-".join(slug_parts)
    #         # Clean up the slug
    #         slug_text = re.sub(r'[^\w\s-]', '', slug_text)  # Remove special chars
    #         slug_text = re.sub(r'\s+', '-', slug_text)      # Replace spaces with hyphens
    #         self.slug = slugify(slug_text)[:300]  # Limit length
    #     super().save(*args, **kwargs)
    # 
    # def get_absolute_url(self):
    #     return reverse("component_detail_seo", args=[self.pk, self.slug])

    # Optional - add a method to get map info
    def map_info(self):
        """Return a dict with info needed for map markers"""
        return {
            'id': self.id,
            'title': self.location or 'Unknown Location',
            'description': self.description or '',
            'technology': self.technology or 'Unknown',
            'company': self.company_name or 'Unknown',
            'cmu_id': self.cmu_id,
            'lat': self.latitude,
            'lng': self.longitude,
            'delivery_year': self.delivery_year or '',
            'url': f'/component/{self.id}/'  # Assuming you have a detail view URL named 'component_detail'
        }


class LocationGroup(models.Model):
    """
    Pre-computed location groups for efficient pagination and display.
    Each unique location has one record with aggregated data about its components.
    """
    location = models.CharField(max_length=255, unique=True, db_index=True)
    component_count = models.IntegerField(default=0, db_index=True)
    
    # SEO-friendly slug (commented out until migration is run)
    # slug = models.SlugField(max_length=300, blank=True, db_index=True)
    
    # Capacity fields - handling aggregation issues
    displayed_capacity_mw = models.FloatField(default=0.0)  # What's shown in raw data
    normalized_capacity_mw = models.FloatField(default=0.0, db_index=True)  # Actual capacity for this location
    capacity_confidence = models.CharField(max_length=20, default='none')  # high/medium/low/none
    
    # Aggregation detection
    is_aggregated_cmu = models.BooleanField(default=False)  # True if CMU spans multiple locations
    cmu_location_count = models.IntegerField(default=1)  # Number of locations in this CMU
    capacity_source = models.CharField(max_length=50, null=True)  # Which field capacity came from
    capacity_calculation_notes = models.TextField(null=True)  # Explanation of calculation
    
    # Store auction years as a sorted JSON list for easy display
    auction_years = models.JSONField(default=list)  # e.g., ["T-4 2019/20", "T-4 2020/21"]
    
    # Store technologies as a JSON dict with counts
    technologies = models.JSONField(default=dict)  # e.g., {"Battery": 3, "Solar": 1}
    
    # Store company names as a JSON dict with counts  
    companies = models.JSONField(default=dict)  # e.g., {"Company A": 2, "Company B": 1}
    
    # Store unique descriptions at this location
    descriptions = models.JSONField(default=list)  # e.g., ["Engine 1", "Engine 2"]
    
    # Store unique CMU IDs at this location  
    cmu_ids = models.JSONField(default=list)  # e.g., ["VIT304", "VIT305", "VIT306"]
    
    # Active status - True if any component has auction year 2024 or later
    is_active = models.BooleanField(default=False, db_index=True)
    
    # Full-text search vector for fast searching across all text fields
    search_vector = SearchVectorField(null=True, blank=True)  # Will be populated by trigger/migration
    
    # Representative component (for getting coordinates, etc.)
    representative_component = models.ForeignKey(
        Component, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='location_groups'
    )
    
    # Geocoding info (copied from representative component)
    latitude = models.FloatField(null=True, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    county = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    outward_code = models.CharField(max_length=5, null=True, blank=True, db_index=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            # For sorting by component count
            models.Index(fields=['-component_count'], name='loc_group_count_idx'),
            # For filtering by county/outward code
            models.Index(fields=['county', 'outward_code'], name='loc_group_geo_idx'),
            # For map queries
            models.Index(fields=['latitude', 'longitude'], name='loc_group_spatial_idx'),
        ]
        ordering = ['-component_count', 'location']
    
    def __str__(self):
        return f"{self.location} ({self.component_count} components)"
    
    # def save(self, *args, **kwargs):
    #     if not self.slug:
    #         # Create slug from location with postcode if available
    #         slug_text = self.location
    #         
    #         # Extract postcode from location if present
    #         postcode_match = re.search(r'([A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2})$', self.location.upper())
    #         if postcode_match:
    #             postcode = postcode_match.group(1).replace(' ', '').lower()
    #             # Clean location without postcode and add postcode at end
    #             location_clean = re.sub(r'[,\s]*[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}$', '', self.location, flags=re.IGNORECASE)
    #             slug_text = f"{location_clean}-{postcode}"
    #         
    #         # Clean up the slug
    #         slug_text = re.sub(r'[^\w\s-]', '', slug_text)  # Remove special chars except hyphens
    #         slug_text = re.sub(r'\s+', '-', slug_text)      # Replace spaces with hyphens
    #         self.slug = slugify(slug_text)[:300]  # Limit length
    #     super().save(*args, **kwargs)
    # 
    # def get_absolute_url(self):
    #     return reverse("location_detail_seo", args=[self.pk, self.slug])
    
    # Cache tech priorities as class variable for performance
    _TECH_PRIORITIES = {
        'EV Charging': 1,
        'Pumped Hydro': 2, 
        'Battery': 3,
        'Nuclear': 4,
        'Interconnector': 5,
        'Solar': 6,
        'Wind': 7,
        'Hydro': 8,
        'CHP': 9,
        'OCGT': 10,
        'Gas': 10,
        'Biomass': 11,
        'Coal': 12,
        'DSR': 13,  # Lower priority, more generic
    }
    
    def get_primary_technology(self):
        """Return the most appropriate technology for this location with priority logic"""
        if not self.technologies:
            return "Unknown"
        
        # Priority order for technology display:
        # 1. EV Charging (more specific than DSR)
        # 2. Pumped Hydro (more specific than general Hydro)
        # 3. Battery (more specific than general Storage)
        # 4. Other specific technologies
        # 5. DSR (catch-all for demand response)
        
        # Use cached priorities instead of creating dict on every call
        tech_priorities = self._TECH_PRIORITIES
        
        # Get the technology with highest priority that exists
        available_techs = list(self.technologies.keys())
        
        # Optimize: Use min() instead of sorting entire list
        if available_techs:
            best_tech = min(available_techs, key=lambda x: tech_priorities.get(x, 999))
            return best_tech
        
        return "Unknown"
    
    def get_primary_company(self):
        """Return the most common company at this location"""
        if not self.companies:
            return "Unknown"
        return max(self.companies.items(), key=lambda x: x[1])[0]
    
    def get_display_capacity(self):
        """Get capacity for display purposes with context"""
        if self.capacity_confidence == 'none':
            return "No capacity data"
        
        if self.is_aggregated_cmu:
            return f"{self.normalized_capacity_mw:.2f} MW (part of {self.displayed_capacity_mw:.2f} MW aggregated CMU)"
        else:
            return f"{self.normalized_capacity_mw:.2f} MW"
    
    def get_sort_capacity(self):
        """Get capacity value for sorting - always use normalized"""
        return self.normalized_capacity_mw
    
    def get_colocation_info(self):
        """Check if there are other LocationGroups at the same exact postcode OR multiple components within this LocationGroup"""
        if not self.representative_component:
            return None
        
        # Get the full postcode from representative component
        full_postcode = self.representative_component.full_postcode
        if not full_postcode:
            return None
        
        # Count total LocationGroups at same postcode
        total_location_groups = LocationGroup.objects.filter(
            representative_component__full_postcode=full_postcode
        ).count()
        
        # Only show co-location if there are multiple LocationGroups at this postcode
        if total_location_groups > 1:
            return {'postcode': full_postcode, 'count': total_location_groups}
        
        return None
    
    def get_business_info(self):
        """Get enhanced business information from representative component"""
        if not self.representative_component:
            return None
        
        rep_comp = self.representative_component
        
        # Return None if no business data available
        if not rep_comp.places_api_business_name:
            return None
        
        return {
            'business_name': rep_comp.places_api_business_name,
            'business_type': rep_comp.places_api_business_type,
            'confidence': rep_comp.places_api_confidence,
            'search_strategy': rep_comp.places_api_search_strategy,
            'major_retailers': rep_comp.places_api_major_retailers or [],
            'last_checked': rep_comp.places_api_last_checked
        }
    
    def get_display_business_name(self):
        """Get business name for display purposes - ONLY for ASDA stores"""
        business_info = self.get_business_info()
        if not business_info:
            return None
        
        # Only show business name if it's an ASDA store
        if 'ASDA' in business_info.get('major_retailers', []):
            return business_info['business_name']
        
        # Don't show any other businesses
        return None
    
    def get_major_retailer_badge(self):
        """Get major retailer for badge display"""
        business_info = self.get_business_info()
        if not business_info or not business_info['major_retailers']:
            return None
        
        # Return first/primary major retailer
        return business_info['major_retailers'][0]
    
    def has_asda_store(self):
        """Check if this location has an ASDA store"""
        business_info = self.get_business_info()
        return business_info and 'ASDA' in business_info.get('major_retailers', [])
    
    def get_business_context(self):
        """Get contextual business information for display"""
        business_info = self.get_business_info()
        if not business_info:
            return None
        
        context = {}
        
        # Add retailer info
        if business_info['major_retailers']:
            context['major_retailer'] = business_info['major_retailers'][0]
            context['all_retailers'] = business_info['major_retailers']
        
        # Add business type context
        business_type = business_info.get('business_type')
        if business_type:
            if business_type in ['supermarket', 'grocery_or_supermarket']:
                context['type_display'] = 'Supermarket'
            elif business_type in ['shopping_mall', 'shopping_center']:
                context['type_display'] = 'Shopping Center'
            elif business_type == 'gas_station':
                context['type_display'] = 'Petrol Station'
            elif business_type in ['route', 'intersection']:
                context['type_display'] = 'Street Address'
            else:
                context['type_display'] = business_type.replace('_', ' ').title()
        else:
            context['type_display'] = 'Business'
        
        return context


class CompanyLinks(models.Model):
    """
    Pre-generated auction links for each company to avoid expensive
    link building during search results display
    """
    company_name = models.CharField(max_length=255, unique=True, db_index=True)
    auction_links = models.JSONField(default=list)  # List of {auction, count, url}
    component_count = models.IntegerField(default=0)
    auction_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Company Links"
        ordering = ['company_name']
    
    def __str__(self):
        return f"{self.company_name} ({self.auction_count} auctions)"
    
    def get_links_html(self):
        """Generate HTML links from stored data"""
        if not self.auction_links:
            return ""
        
        links = []
        for auction_data in self.auction_links:
            link = f'<a href="{auction_data["url"]}" class="auction-link">{auction_data["auction"]} ({auction_data["count"]})</a>'
            links.append(link)
        
        return ' | '.join(links)


class CMURegistry(models.Model):
    cmu_id = models.CharField(max_length=100, primary_key=True, unique=True)
    raw_data = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        applicant = self.raw_data.get('Name of Applicant', 'Unknown')
        return f"{self.cmu_id} ({applicant})"
