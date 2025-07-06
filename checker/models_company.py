from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, SearchVector
import logging

logger = logging.getLogger(__name__)

class Company(models.Model):
    """
    Company model with full-text search capabilities.
    Replaces the Redis-based company index with proper database storage.
    """
    # Core company data
    name = models.CharField(max_length=255, unique=True, db_index=True)
    normalized_name = models.CharField(max_length=255, db_index=True)
    
    # Pre-computed search data
    component_count = models.IntegerField(default=0)
    total_capacity_mw = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Pre-computed HTML (replaces Redis serialized data)
    search_result_html = models.TextField(blank=True)
    
    # Full-text search vector (commented out for now)
    # search_vector = SearchVectorField(null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_component_update = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'checker_company'
        indexes = [
            # Full-text search index (commented out for now)
            # GinIndex(fields=['search_vector']),
            # Fast lookups
            models.Index(fields=['normalized_name']),
            models.Index(fields=['component_count']),
            models.Index(fields=['total_capacity_mw']),
            # Updated tracking
            models.Index(fields=['last_component_update']),
        ]
    
    def __str__(self):
        return self.name
    
    @classmethod
    def rebuild_search_data(cls):
        """
        Rebuild all company search data from Component table.
        Uses efficient bulk operations.
        """
        from django.db import transaction
        from django.apps import apps
        
        logger.info("Starting company search data rebuild...")
        
        # Get Component model to avoid circular imports
        Component = apps.get_model('checker', 'Component')
        
        # Clear existing companies
        cls.objects.all().delete()
        logger.info("Cleared existing companies")
        
        # Get all companies from components efficiently
        companies_to_create = []
        
        # Get unique companies with their stats
        company_stats = Component.objects.values('company_name').annotate(
            component_count=models.Count('id'),
            total_capacity=models.Sum('derated_capacity_mw')
        ).filter(
            company_name__isnull=False
        ).exclude(
            company_name__exact=''
        )
        
        logger.info(f"Processing {company_stats.count()} companies...")
        
        for stats in company_stats:
            name = stats['company_name']
            normalized_name = name.lower().strip()
            component_count = stats['component_count']
            total_capacity = stats['total_capacity'] or 0
            
            # Build simple HTML for search results
            search_html = f'<div><strong><a href="/companies/{name}/">{name}</a></strong> ({component_count} components, {total_capacity:.1f} MW)</div>'
            
            companies_to_create.append(cls(
                name=name,
                normalized_name=normalized_name,
                component_count=component_count,
                total_capacity_mw=total_capacity,
                search_result_html=search_html
            ))
        
        # Bulk create all companies
        cls.objects.bulk_create(companies_to_create, batch_size=100)
        created_count = len(companies_to_create)
        
        logger.info(f"Company rebuild complete: {created_count} companies created")
        
        return created_count, 0
    
    @classmethod
    def _build_search_html(cls, company, data):
        """Build the HTML for search results (replaces Redis serialization)."""
        return f"""
        <div class="company-result">
            <h5>{company.name}</h5>
            <p>{data['component_count']} components, {data['total_capacity'] or 0:.1f} MW total</p>
        </div>
        """
    
    @classmethod
    def search_companies(cls, query, limit=50):
        """
        Fast company search using simple LIKE queries.
        Replaces the Redis-based fuzzy search.
        """
        if not query or len(query.strip()) < 2:
            return cls.objects.none()
        
        query = query.strip().lower()
        
        # Use simple LIKE search for now (can upgrade to full-text later)
        return cls.objects.filter(
            normalized_name__icontains=query
        ).order_by(
            '-component_count', 'name'
        )[:limit]
    
    @classmethod
    def search_companies_fuzzy(cls, query, limit=50):
        """
        Fallback fuzzy search if full-text search returns no results.
        Much faster than Redis approach since it's a simple SQL LIKE query.
        """
        if not query or len(query.strip()) < 2:
            return cls.objects.none()
        
        query = query.strip().lower()
        
        return cls.objects.filter(
            normalized_name__icontains=query
        ).order_by(
            '-component_count', 'name'
        )[:limit]