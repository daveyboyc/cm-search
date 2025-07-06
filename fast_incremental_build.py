#!/usr/bin/env python
"""Fast incremental LocationGroup builder with automatic retries."""

import os
import sys
import time
import logging

# Suppress startup messages
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
import django
django.setup()

# Re-enable logging after setup
logging.disable(logging.NOTSET)

from django.core.management import call_command
from checker.models import LocationGroup, Component

def get_coverage():
    """Get current coverage percentage."""
    lg_count = LocationGroup.objects.count()
    components_covered = sum(LocationGroup.objects.values_list('component_count', flat=True))
    total_components = Component.objects.count()
    coverage = (components_covered / total_components * 100) if total_components > 0 else 0
    return lg_count, coverage

def main():
    print("=== Fast Incremental LocationGroup Builder ===")
    print("Building in batches of 100 with 2-second breaks")
    print("Press Ctrl+C to stop at any time\n")
    
    batch_size = 100
    sleep_time = 2
    
    while True:
        # Get current status
        lg_count, coverage = get_coverage()
        print(f"\nCurrent: {lg_count:,} LocationGroups ({coverage:.1f}% coverage)")
        
        if coverage >= 80:
            print("\n🎉 SUCCESS! LocationGroups are now ACTIVE! (80% coverage reached)")
            break
        
        try:
            # Run build command
            print(f"Building next {batch_size} locations...", end='', flush=True)
            start = time.time()
            
            # Capture output to avoid clutter
            from io import StringIO
            import sys
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                call_command('build_location_groups_incremental', batch=batch_size)
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                # Extract created count from output
                created = 0
                for line in output.split('\n'):
                    if 'Created:' in line and 'new LocationGroups' in line:
                        created = int(line.split('Created:')[1].split('new')[0].strip())
                
                elapsed = time.time() - start
                print(f" ✓ Created {created} in {elapsed:.1f}s")
                
                if created == 0:
                    print("\nNo new LocationGroups created. All done!")
                    break
                    
            except Exception as e:
                sys.stdout = old_stdout
                print(f" ✗ Error: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
                continue
                
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
            lg_count, coverage = get_coverage()
            print(f"Final: {lg_count:,} LocationGroups ({coverage:.1f}% coverage)")
            break
        
        # Brief pause between batches
        print(f"Sleeping {sleep_time}s...", end='', flush=True)
        time.sleep(sleep_time)
        print(" ready!")

if __name__ == '__main__':
    main()