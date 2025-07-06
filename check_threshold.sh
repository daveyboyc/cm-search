#!/bin/bash
cd /Users/davidcrawford/PycharmProjects/cmr
source venv/bin/activate
python manage.py shell -c "
from checker.services.location_group_check import should_use_location_groups
from checker.models import LocationGroup, Component
lg_count = LocationGroup.objects.count()
components_covered = sum(LocationGroup.objects.values_list('component_count', flat=True))
total_components = Component.objects.count()
coverage = (components_covered / total_components * 100) if total_components > 0 else 0
print(f'LocationGroups: {lg_count:,}')
print(f'Coverage: {coverage:.1f}%')
print(f'Using LocationGroups: {should_use_location_groups()}')"