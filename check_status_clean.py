#!/usr/bin/env python
"""Check LocationGroup build status with clean output."""

import os
import sys
import logging

# Suppress all startup messages
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')

# Suppress Django startup messages
import django
django.setup()

# Re-enable logging after setup
logging.disable(logging.NOTSET)

from checker.models import LocationGroup, Component
from checker.services.location_group_check import should_use_location_groups
from django.db.models import Q

# Get stats
lg_count = LocationGroup.objects.count()
components_covered = sum(LocationGroup.objects.values_list('component_count', flat=True))
total_components = Component.objects.count()
coverage = (components_covered / total_components * 100) if total_components > 0 else 0

# Clean output
print(f"LocationGroups: {lg_count:,}")
print(f"Coverage: {coverage:.1f}%")
print(f"Status: {'✅ ACTIVE' if should_use_location_groups() else '❌ INACTIVE (need 80%)'}")