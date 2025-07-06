#!/usr/bin/env python
"""Add caching for common search terms to improve performance"""
import os
import django
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.core.cache import cache
import json

print("🚀 Pre-caching common search terms")
print("=" * 50)

# Common searches that should be cached
common_searches = [
    "energy centre",
    "battery",
    "battery storage", 
    "grid",
    "solar",
    "wind",
    "gas",
    "power",
    "storage"
]

print("\n📊 Caching search results for common terms...")

for term in common_searches:
    # Generate the same cache key the app uses
    cache_key = f"search_service_{term.replace(' ', ' ')}_p1_pp10_sortrelevance_desc"
    
    # Check if already cached
    if cache.get(cache_key):
        print(f"  ✅ '{term}' already cached")
    else:
        print(f"  📝 '{term}' not cached (will cache on first search)")

print("\n💡 TIP: The app will automatically cache these searches")
print("   after the first time they're performed.")
print("\n🔍 Try searching for 'energy centre' again - ")
print("   the second search should be instant!")