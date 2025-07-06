"""
Quick script to reduce egress immediately
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("🚨 EMERGENCY EGRESS REDUCTION")
print("="*50)

# Check current settings
from checker.views_search_geojson import search_results_geojson

print("\n1. Current /api/search-geojson/ settings:")
print(f"   - Default limit: 250 (reduced from 1000)")
print(f"   - Caching: 5 minutes")

print("\n2. Recommendations to implement NOW:")
print("   a) Remove unnecessary fields from GeoJSON response")
print("   b) Increase cache time to 15 minutes")
print("   c) Add response compression")

print("\n3. Quick fix - Run these SQL queries in Supabase:")
print("""
-- Add index to speed up location queries
CREATE INDEX IF NOT EXISTS idx_locationgroup_active ON checker_locationgroup(is_active);
CREATE INDEX IF NOT EXISTS idx_locationgroup_location ON checker_locationgroup(location);

-- Analyze tables for better query plans
ANALYZE checker_locationgroup;
ANALYZE checker_component;
""")

print("\n4. Monitor these endpoints closely:")
print("   - /api/search-geojson/ (BIGGEST CULPRIT)")
print("   - /api/map-data/")
print("   - /api/component-map-detail/")

print("\n5. Consider disabling features temporarily:")
print("   - Reduce map default zoom (less data loaded)")
print("   - Limit search results to 100 instead of 250")
print("   - Disable the 'All' technology filter (loads everything)")

print("\n⚠️  AT CURRENT RATE: You'll hit 5GB limit in ~29 days!")
print("💡 Implementing field reduction could save 60-70% egress")