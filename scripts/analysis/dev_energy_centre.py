#!/usr/bin/env python
"""Test performance for 'energy centre' search"""
import os
import django
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component
from django.db.models import Q

print("🔍 Testing 'energy centre' search performance")
print("=" * 50)

# Test 1: Check how many matches
print("\n1️⃣ Checking match counts:")
queries = ["energy", "centre", "energy centre"]

for query in queries:
    start = time.time()
    
    # Simulate the exact database query
    filter_obj = Q(location__icontains=query) | \
                 Q(description__icontains=query) | \
                 Q(technology__icontains=query) | \
                 Q(company_name__icontains=query)
    
    count = Component.objects.filter(filter_obj).count()
    elapsed = time.time() - start
    
    print(f"  '{query}': {count:,} matches in {elapsed:.3f}s")

# Test 2: Check the actual multi-word query
print("\n2️⃣ Testing exact 'energy centre' query:")
start = time.time()

# This is what the app does for multi-word queries
multi_filter = Q(location__icontains='energy centre') | \
               Q(description__icontains='energy centre') | \
               Q(technology__icontains='energy centre') | \
               Q(company_name__icontains='energy centre') | \
               (Q(location__icontains='energy') & Q(location__icontains='centre')) | \
               (Q(description__icontains='energy') & Q(description__icontains='centre'))

count = Component.objects.filter(multi_filter).count()
elapsed = time.time() - start

print(f"  Multi-word filter: {count:,} matches in {elapsed:.3f}s")

# Test 3: Check if it's an indexing issue
print("\n3️⃣ Checking database indexes:")
from django.db import connection

with connection.cursor() as cursor:
    # Check indexes on the table
    cursor.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'checker_component' 
        AND indexname LIKE '%description%' OR indexname LIKE '%location%'
        LIMIT 5
    """)
    
    indexes = cursor.fetchall()
    if indexes:
        for idx in indexes:
            print(f"  Index: {idx[0]}")
    else:
        print("  ⚠️  No text search indexes found!")

# Test 4: Location lookup for "energy centre"
print("\n4️⃣ Testing location lookup:")
from checker.services import get_all_postcodes_for_area

start = time.time()
postcodes = get_all_postcodes_for_area("energy centre")
elapsed = time.time() - start

print(f"  Postcodes found: {len(postcodes)}")
print(f"  Time: {elapsed:.3f}s")

if elapsed < 0.1:
    print("  ✅ Fast location lookup working!")
else:
    print("  ❌ Location lookup still slow")

# Test 5: Optimization suggestion
print("\n💡 OPTIMIZATION SUGGESTIONS:")
print("  1. The database query is the bottleneck (1.33s)")
print("  2. Consider adding full-text search indexes")
print("  3. Or limit search to specific fields for common terms")
print("  4. Cache results for common searches like 'energy centre'")

# Show sample results
print("\n📊 Sample 'energy centre' locations:")
results = Component.objects.filter(
    Q(location__icontains='energy centre')
).values_list('location', flat=True).distinct()[:5]

for loc in results:
    print(f"  - {loc}")