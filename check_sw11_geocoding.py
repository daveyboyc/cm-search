"""
Script to check geocoding status of SW11 components
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

# Now import Django models
from checker.models import Component
from django.db.models import Q

def main():
    """Check SW11 component geocoding status"""
    # Count total components
    total_count = Component.objects.count()
    print(f"Total components in database: {total_count}")
    
    # Count geocoded components
    geocoded_count = Component.objects.filter(geocoded=True).count()
    print(f"Total geocoded components: {geocoded_count} ({geocoded_count/total_count*100:.1f}%)")
    
    # Find SW11 components regardless of geocoding
    sw11_components = Component.objects.filter(
        Q(location__icontains='sw11') | 
        Q(cmu_id__icontains='sw11') |
        Q(company_name__icontains='sw11')
    )
    print(f"Total components matching SW11 search: {sw11_components.count()}")
    
    # Count SW11 components that are geocoded
    sw11_geocoded = sw11_components.filter(geocoded=True, latitude__isnull=False, longitude__isnull=False)
    print(f"SW11 components that are geocoded: {sw11_geocoded.count()}")
    
    # Print details of SW11 components
    print("\nSW11 components (first 10):")
    for comp in sw11_components[:10]:
        print(f"- ID: {comp.id}, CMU ID: {comp.cmu_id}, Location: {comp.location}")
        print(f"  Geocoded: {comp.geocoded}, Lat/Lng: {comp.latitude}/{comp.longitude}")
        print()
    
    # Print geocoding status details
    if sw11_geocoded.count() == 0:
        print("\nNo SW11 components are geocoded. This explains why they don't appear on the map.")
        print("The map API filters for geocoded=True, latitude__isnull=False, longitude__isnull=False")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())