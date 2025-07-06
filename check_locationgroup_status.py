#!/usr/bin/env python
"""Check the current status of LocationGroup building."""

import os
import sys
import django

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup, Component
from django.db.models import Q

# Get stats
total_components = Component.objects.count()
total_locations = Component.objects.exclude(
    Q(location__isnull=True) |
    Q(location='') |
    Q(location='None') |
    Q(location='N/A') |
    Q(location='NA') |
    Q(location__icontains='TBC') |
    Q(location__icontains='to be confirmed')
).values_list('location', flat=True).distinct().count()

location_groups = LocationGroup.objects.count()
components_covered = sum(LocationGroup.objects.values_list('component_count', flat=True))
coverage_percentage = (components_covered / total_components * 100) if total_components > 0 else 0
location_coverage = (location_groups / total_locations * 100) if total_locations > 0 else 0

print("=== LocationGroup Build Status ===")
print(f"Total components: {total_components:,}")
print(f"Total unique locations: {total_locations:,}")
print(f"LocationGroups built: {location_groups:,} ({location_coverage:.1f}% of locations)")
print(f"Components covered: {components_covered:,} ({coverage_percentage:.1f}% of components)")
print(f"Components per location avg: {components_covered/location_groups:.1f}" if location_groups > 0 else "N/A")
print(f"\nNeed 80% component coverage to activate. Current: {coverage_percentage:.1f}%")
print(f"Estimated LocationGroups needed: ~{int(total_locations * 0.8):,}")

# Show most recent LocationGroups
recent = LocationGroup.objects.order_by('-id')[:5]
if recent:
    print("\nMost recently built LocationGroups:")
    for lg in recent:
        print(f"  - {lg.location[:50]}... ({lg.component_count} components)")