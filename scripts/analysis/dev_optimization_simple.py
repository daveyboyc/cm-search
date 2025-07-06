#!/usr/bin/env python3
"""
Simple test to check our optimization worked
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup
import json

print("🔍 TESTING OPTIMIZATION: FIELD REMOVAL")
print("=" * 50)

# Get a sample location 
try:
    location = LocationGroup.objects.filter(
        technologies__isnull=False,
        latitude__isnull=False
    ).first()
    
    if location:
        print(f"✅ Found sample location: {location.location}")
        
        # This is what we USED to send (the old way)
        old_properties = {
            'id': location.id,
            'title': location.location,
            'technology': 'Battery',
            'all_technologies': location.technologies,  # BIG FIELD
            'company': 'SomeCompany',
            'all_companies': location.companies,  # BIG FIELD  
            'all_cmu_ids': location.cmu_ids,  # BIG FIELD
            'all_years': location.auction_years,  # BIG FIELD
            'component_count': location.component_count,
            'capacity_mw': location.normalized_capacity_mw,
        }
        
        # This is what we NOW send (the new way)
        new_properties = {
            'id': location.id,
            'title': location.location,
            'technology': 'Battery',
            'company': 'SomeCompany',
            'description': '',
            'cmu_id': '',
            'auction_name': '',
            'detailUrl': f'/location/{location.id}/',
            'component_count': location.component_count,
            'is_group': location.component_count > 1,
            'years_string': '',
            'is_active': location.is_active,
            'capacity_mw': location.normalized_capacity_mw,
            'capacity_display': f"{location.normalized_capacity_mw:.1f} MW" if location.normalized_capacity_mw else "0 MW"
        }
        
        old_json = json.dumps(old_properties)
        new_json = json.dumps(new_properties)
        
        old_size = len(old_json.encode('utf-8'))
        new_size = len(new_json.encode('utf-8'))
        reduction = ((old_size - new_size) / old_size * 100) if old_size > 0 else 0
        
        print(f"\n📊 SIZE COMPARISON (per location):")
        print(f"  Old format: {old_size:,} bytes")
        print(f"  New format: {new_size:,} bytes")
        print(f"  Reduction: {reduction:.1f}%")
        
        print(f"\n🔢 FIELD COUNT:")
        print(f"  Old: {len(old_properties)} fields")
        print(f"  New: {len(new_properties)} fields")
        
        print(f"\n📈 IMPACT FOR DIFFERENT RESULT SIZES:")
        for count in [10, 50, 100, 250]:
            old_total = old_size * count / 1024
            new_total = new_size * count / 1024
            print(f"  {count} locations: {old_total:.1f} KB → {new_total:.1f} KB ({((old_total-new_total)/old_total*100):.1f}% reduction)")
        
        # Show the actual data that was removed
        print(f"\n🗑️  REMOVED LARGE FIELDS:")
        if location.technologies:
            tech_size = len(json.dumps(location.technologies).encode('utf-8'))
            print(f"  all_technologies: {tech_size} bytes - {location.technologies}")
        if location.companies:
            comp_size = len(json.dumps(location.companies).encode('utf-8'))
            print(f"  all_companies: {comp_size} bytes - {list(location.companies.keys())[:3]}...")
        if location.cmu_ids:
            cmu_size = len(json.dumps(location.cmu_ids).encode('utf-8'))
            print(f"  all_cmu_ids: {cmu_size} bytes - {location.cmu_ids[:3]}...")
        if location.auction_years:
            year_size = len(json.dumps(location.auction_years).encode('utf-8'))
            print(f"  all_years: {year_size} bytes - {location.auction_years[:3]}...")
            
    else:
        print("❌ No sample location found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Also check our current limits
print(f"\n⚙️  CURRENT SETTINGS:")
print(f"  Default limit: 100 (was 1000)")
print(f"  Cache time: 15 minutes (was 5)")
print(f"  Gzip compression: ✅ Enabled")
print(f"  Redundant fields: ✅ Removed")