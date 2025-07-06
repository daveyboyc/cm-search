#!/usr/bin/env python
"""Test that the fast imports are working correctly"""
import os
import django
import sys

# Set up Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("🔍 Testing import fixes...")
print("=" * 50)

# Test 1: Check services/__init__.py
print("\n1️⃣ Testing services/__init__.py import:")
try:
    from checker.services import get_all_postcodes_for_area
    print("✅ Successfully imported from services")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Check component_search.py
print("\n2️⃣ Testing component_search.py import:")
try:
    import checker.services.component_search
    # Force reload to pick up changes
    import importlib
    importlib.reload(checker.services.component_search)
    print("✅ component_search.py reloaded successfully")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Actually test the speed
print("\n3️⃣ Testing actual performance:")
import time

start = time.time()
result = get_all_postcodes_for_area("battery")
elapsed = time.time() - start

print(f"   Result: {len(result)} postcodes")
print(f"   Time: {elapsed:.3f}s")

if elapsed < 0.1:
    print("   ✅ FAST lookup is working!")
else:
    print("   ❌ Still using SLOW lookup")

# Test 4: Check what's being logged
print("\n4️⃣ Checking imports in component_search:")
with open('checker/services/component_search.py', 'r') as f:
    content = f.read()
    if 'postcode_helpers_fast' in content:
        print("✅ component_search.py has been updated to use fast imports")
    else:
        print("❌ component_search.py still using old imports")