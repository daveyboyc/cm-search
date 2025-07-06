#!/usr/bin/env python
import os
import sys
import django
from collections import Counter, defaultdict

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import Component, CMURegistry
from django.db.models import Count, Q
import json

def analyze_capacity_fields():
    """Analyze what capacity fields are available across all components"""
    print("\nCAPACITY FIELD ANALYSIS")
    print("=" * 80)
    
    # Check derated capacity availability
    total_components = Component.objects.count()
    with_derated = Component.objects.filter(derated_capacity_mw__isnull=False).count()
    without_derated = Component.objects.filter(derated_capacity_mw__isnull=True).count()
    
    print(f"Total components: {total_components:,}")
    print(f"With derated_capacity_mw: {with_derated:,} ({with_derated/total_components*100:.1f}%)")
    print(f"Without derated_capacity_mw: {without_derated:,} ({without_derated/total_components*100:.1f}%)")
    
    # Check additional_data fields for capacity info
    print("\nAnalyzing additional_data fields for capacity information...")
    
    capacity_field_counts = Counter()
    sample_capacity_values = defaultdict(list)
    
    # Sample 5000 components to analyze additional_data
    components = Component.objects.all()[:5000]
    
    for comp in components:
        if comp.additional_data:
            for key, value in comp.additional_data.items():
                # Look for capacity-related fields
                key_lower = key.lower()
                if any(term in key_lower for term in ['capacity', 'mw', 'power', 'connection', 'derated', 'anticipated']):
                    capacity_field_counts[key] += 1
                    if len(sample_capacity_values[key]) < 5:
                        sample_capacity_values[key].append({
                            'value': value,
                            'component_id': comp.id,
                            'location': comp.location[:50] + '...' if len(comp.location or '') > 50 else comp.location
                        })
    
    print(f"\nCapacity-related fields found in additional_data (from {len(components)} sample):")
    for field, count in capacity_field_counts.most_common(20):
        print(f"  '{field}': {count} occurrences")
        # Show sample values
        if field in sample_capacity_values:
            for sample in sample_capacity_values[field][:2]:
                print(f"    Example: {sample['value']} (Component #{sample['component_id']})")

def analyze_cmu_registry_capacity():
    """Analyze capacity data in CMU Registry"""
    print("\n\nCMU REGISTRY CAPACITY ANALYSIS")
    print("=" * 80)
    
    total_cmus = CMURegistry.objects.count()
    print(f"Total CMU Registry entries: {total_cmus:,}")
    
    # Sample CMU registry entries to find capacity fields
    capacity_fields = Counter()
    sample_values = defaultdict(list)
    
    cmus = CMURegistry.objects.all()[:1000]
    
    for cmu in cmus:
        if cmu.raw_data:
            for key, value in cmu.raw_data.items():
                key_lower = key.lower()
                if any(term in key_lower for term in ['capacity', 'mw', 'power', 'connection', 'derated']):
                    capacity_fields[key] += 1
                    if len(sample_values[key]) < 3:
                        sample_values[key].append({
                            'value': value,
                            'cmu_id': cmu.cmu_id
                        })
    
    print(f"\nCapacity fields in CMU Registry (from {len(cmus)} sample):")
    for field, count in capacity_fields.most_common(15):
        print(f"  '{field}': {count} occurrences")
        if field in sample_values:
            for sample in sample_values[field][:1]:
                print(f"    Example: {sample['value']} (CMU: {sample['cmu_id']})")

def test_capacity_calculation_methods():
    """Test different methods for calculating location capacity"""
    print("\n\nCAPACITY CALCULATION METHODS TEST")
    print("=" * 80)
    
    # Test on a location with multiple components
    test_location = "Imperial College London"
    
    components = Component.objects.filter(location__icontains=test_location)
    
    print(f"\nTesting with {test_location}:")
    print(f"Total components: {components.count()}")
    
    # Method 1: Use derated capacity where available
    derated_values = [c.derated_capacity_mw for c in components if c.derated_capacity_mw]
    print(f"\nMethod 1 - Derated Capacity:")
    print(f"  Components with data: {len(derated_values)}/{components.count()}")
    if derated_values:
        print(f"  Values: {derated_values}")
        print(f"  Sum: {sum(derated_values):.2f} MW")
        print(f"  Average: {sum(derated_values)/len(derated_values):.2f} MW")
    
    # Method 2: Check additional_data for other capacity fields
    print(f"\nMethod 2 - Additional Data Fields:")
    other_capacity_data = defaultdict(list)
    
    for comp in components:
        if comp.additional_data:
            for key, value in comp.additional_data.items():
                if 'capacity' in key.lower() or 'mw' in key.lower():
                    try:
                        # Try to extract numeric value
                        if isinstance(value, (int, float)):
                            other_capacity_data[key].append(float(value))
                        elif isinstance(value, str):
                            # Try to extract number from string
                            import re
                            numbers = re.findall(r'[\d.]+', value)
                            if numbers:
                                other_capacity_data[key].append(float(numbers[0]))
                    except:
                        pass
    
    for field, values in other_capacity_data.items():
        print(f"  {field}: {values}")
    
    # Method 3: Group by description and use max value per group
    print(f"\nMethod 3 - Group by Description:")
    by_description = defaultdict(list)
    for comp in components:
        if comp.derated_capacity_mw:
            by_description[comp.description].append(comp.derated_capacity_mw)
    
    for desc, values in by_description.items():
        print(f"  {desc[:60]}...")
        print(f"    Values: {values}")
        print(f"    Max: {max(values):.2f} MW")

def find_best_capacity_source():
    """Determine the best source for capacity data across all components"""
    print("\n\nBEST CAPACITY SOURCE ANALYSIS")
    print("=" * 80)
    
    # Sample 10,000 components
    components = Component.objects.all()[:10000]
    
    capacity_sources = {
        'derated_capacity_mw': 0,
        'additional_data_sources': defaultdict(int)
    }
    
    for comp in components:
        # Check derated capacity
        if comp.derated_capacity_mw is not None:
            capacity_sources['derated_capacity_mw'] += 1
        
        # Check additional data
        if comp.additional_data:
            for key, value in comp.additional_data.items():
                if any(term in key.lower() for term in ['capacity', 'mw', 'connection']):
                    if value and str(value).strip() and str(value).lower() not in ['none', 'n/a', 'null', '-']:
                        capacity_sources['additional_data_sources'][key] += 1
    
    print(f"From {len(components):,} sampled components:")
    print(f"\nPrimary field availability:")
    print(f"  derated_capacity_mw: {capacity_sources['derated_capacity_mw']:,} ({capacity_sources['derated_capacity_mw']/len(components)*100:.1f}%)")
    
    print(f"\nTop additional_data capacity fields:")
    for field, count in sorted(capacity_sources['additional_data_sources'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {field}: {count:,} ({count/len(components)*100:.1f}%)")

if __name__ == "__main__":
    analyze_capacity_fields()
    analyze_cmu_registry_capacity()
    test_capacity_calculation_methods()
    find_best_capacity_source()