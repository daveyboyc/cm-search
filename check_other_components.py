#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
django.setup()

# Now we can import Django models
from checker.models import Component
from checker.views import get_simplified_technology

# Find technologies that map to "Other"
print("Technologies categorized as 'Other':")
other_technologies = []
for tech in Component.objects.values_list('technology', flat=True).distinct():
    if tech and get_simplified_technology(tech) == 'Other':
        other_technologies.append(tech)
        count = Component.objects.filter(technology=tech).count()
        geocoded = Component.objects.filter(technology=tech, latitude__isnull=False, longitude__isnull=False).count()
        print(f"- {tech}: {count} total, {geocoded} geocoded")

print(f"\nTotal distinct 'Other' technologies: {len(other_technologies)}")

# Check if there are any geocoded components in the "Other" category
other_geocoded = 0
for tech in other_technologies:
    other_geocoded += Component.objects.filter(technology=tech, latitude__isnull=False, longitude__isnull=False).count()

print(f"Total geocoded 'Other' components: {other_geocoded}")

# Check default year filter impact
default_year_filter = 2025
year_filter_count = 0
for tech in other_technologies:
    year_filter_count += Component.objects.filter(
        technology=tech, 
        latitude__isnull=False, 
        longitude__isnull=False,
        delivery_year__gte=str(default_year_filter)
    ).count()

print(f"'Other' components passing year filter (>= {default_year_filter}): {year_filter_count}") 