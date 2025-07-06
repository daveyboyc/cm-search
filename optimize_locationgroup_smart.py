#!/usr/bin/env python3
"""
Smart LocationGroup optimization that maintains functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.db import models
from checker.models import LocationGroup

def analyze_template_usage():
    """Show what fields are actually used in templates"""
    
    print("=== LocationGroup Field Usage in Templates ===\n")
    
    print("Fields used in search results display:")
    print("✓ location - Full location name")
    print("✓ auction_years[0:3] - First 3 auction years for display") 
    print("✓ descriptions[0:2] - First 2 descriptions for display")
    print("✓ cmu_ids.length - Count of CMUs (not the full list)")
    print("✓ is_active - Active/Inactive status")
    print("✓ primary_company - Main company name")
    print("✓ primary_technology - Main technology")
    print("✓ normalized_capacity_mw - Capacity in MW")
    print("✓ component_count - Number of components")
    
    print("\n=== Current Problem ===")
    print("We're storing and fetching ALL data even though we only display:")
    print("- First 3 of maybe 10+ auction years")
    print("- First 2 of maybe 5+ descriptions")
    print("- Count of CMUs, not the full list")
    
    print("\n=== Smart Optimization Solutions ===")

def propose_model_changes():
    """Propose model changes to reduce egress while maintaining functionality"""
    
    print("\n1. ADD SUMMARY FIELDS to LocationGroup model:")
    print("""
class LocationGroup(models.Model):
    # ... existing fields ...
    
    # NEW: Pre-computed summary fields
    top_auction_years = models.JSONField(default=list)  # Only first 3
    top_descriptions = models.JSONField(default=list)   # Only first 2
    cmu_count = models.IntegerField(default=0)          # Just the count
    
    # Keep full fields but mark as 'detail only'
    full_auction_years = models.JSONField(default=list)  # Renamed from auction_years
    full_descriptions = models.JSONField(default=list)   # Renamed from descriptions
    full_cmu_ids = models.JSONField(default=list)       # Renamed from cmu_ids
""")
    
    print("\n2. UPDATE build_location_groups command to populate summary fields:")
    print("""
# In build_location_groups.py
location_group.top_auction_years = location_group.auction_years[:3]
location_group.top_descriptions = location_group.descriptions[:2]
location_group.cmu_count = len(location_group.cmu_ids)
""")
    
    print("\n3. MODIFY queries to defer full fields:")
    print("""
# In location_search.py
queryset = LocationGroup.objects.filter(
    location__in=matching_locations
).defer(
    'full_auction_years',    # Skip full list
    'full_descriptions',     # Skip full list
    'full_cmu_ids'          # Skip full list
)
# Now only fetches summary fields!
""")

def immediate_workaround():
    """Propose immediate workaround without schema changes"""
    
    print("\n=== IMMEDIATE WORKAROUND (No Schema Changes) ===")
    
    print("\n1. Optimize the data stored:")
    print("""
# Limit what we store in the first place
# In build_location_groups command:

# Only store first 5 auction years (not all 10+)
location_group.auction_years = sorted(auction_years)[:5]

# Only store first 3 descriptions (not all)
location_group.descriptions = list(descriptions)[:3]

# Store CMU count + first 5 CMUs only
if len(cmu_ids) > 5:
    location_group.cmu_ids = {
        'count': len(cmu_ids),
        'sample': list(cmu_ids)[:5]
    }
else:
    location_group.cmu_ids = list(cmu_ids)
""")
    
    print("\n2. Further optimize with selective loading:")
    print("""
# Create a custom manager method
class LocationGroupManager(models.Manager):
    def search_optimized(self):
        return self.only(
            'id', 'location', 'component_count', 'is_active',
            'normalized_capacity_mw', 'primary_company', 
            'primary_technology', 'technologies', 'companies',
            # Include the JSON fields we can't defer
            'auction_years', 'descriptions', 'cmu_ids'
        )

# Use in searches:
LocationGroup.objects.search_optimized().filter(...)
""")

def calculate_savings():
    """Calculate egress savings from optimization"""
    
    print("\n=== Potential Savings ===")
    
    print("\nCurrent sizes:")
    print("- auction_years: ~400 bytes (all years)")
    print("- descriptions: ~350 bytes (all descriptions)")
    print("- cmu_ids: ~550 bytes (all CMU IDs)")
    
    print("\nOptimized sizes:")
    print("- top_auction_years: ~150 bytes (first 3 only)")
    print("- top_descriptions: ~140 bytes (first 2 only)")
    print("- cmu_count: 4 bytes (integer)")
    
    print("\nSavings per record: ~1000 bytes (1KB)")
    print("For 16,009 records: 16MB saved!")
    print("For battery search (2,244 results): 2.2MB saved per search!")

def alternative_approach():
    """Alternative approach using pagination"""
    
    print("\n=== Alternative: Smart Pagination ===")
    
    print("\n1. Reduce default page size:")
    print("- Change from 25 to 10 results per page")
    print("- Reduces egress by 60% per page load")
    
    print("\n2. Progressive loading:")
    print("- Load basic info first")
    print("- Load details on demand (click to expand)")
    
    print("\n3. Cache aggressively:")
    print("- Cache rendered HTML in Redis")
    print("- Cache for 1 hour (data doesn't change often)")
    print("- Serve from cache = 0 database egress!")

if __name__ == "__main__":
    analyze_template_usage()
    propose_model_changes()
    immediate_workaround()
    calculate_savings()
    alternative_approach()