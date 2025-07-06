#!/usr/bin/env python
"""Build LocationGroups to 80% coverage with better progress tracking."""

import os
import sys
import time
import subprocess

# Setup environment
os.chdir('/Users/davidcrawford/PycharmProjects/cmr')

def get_status():
    """Get current LocationGroup status."""
    cmd = ['./venv/bin/python', 'check_status_clean.py']
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()
    
    # Parse the output
    lines = output.split('\n')
    count = 0
    coverage = 0.0
    
    for line in lines:
        if line.startswith('LocationGroups:'):
            count = int(line.split(':')[1].strip().replace(',', ''))
        elif line.startswith('Coverage:'):
            coverage = float(line.split(':')[1].strip().rstrip('%'))
    
    return count, coverage

def main():
    print("=== Building LocationGroups to 80% Coverage ===")
    print("This will take approximately 10-15 minutes\n")
    
    batch_size = 200  # Larger batches for faster completion
    total_batches = 0
    start_time = time.time()
    
    while True:
        # Get current status
        count, coverage = get_status()
        print(f"\rProgress: {count:,} LocationGroups ({coverage:.1f}% coverage)", end='', flush=True)
        
        if coverage >= 80:
            print(f"\n\n🎉 SUCCESS! LocationGroups are now ACTIVE!")
            print(f"Final: {count:,} LocationGroups ({coverage:.1f}% coverage)")
            print(f"Total time: {(time.time() - start_time) / 60:.1f} minutes")
            break
        
        # Run build command
        cmd = [
            './venv/bin/python', 'manage.py', 
            'build_location_groups_incremental', 
            '--batch', str(batch_size)
        ]
        
        # Run silently (suppress output)
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        total_batches += 1
        
        # Brief pause
        time.sleep(1)
        
        # Show more detailed progress every 10 batches
        if total_batches % 10 == 0:
            elapsed = (time.time() - start_time) / 60
            rate = (coverage - 53.7) / elapsed if elapsed > 0 else 0
            eta = (80 - coverage) / rate if rate > 0 else 0
            print(f"\n  Elapsed: {elapsed:.1f} min | Rate: {rate:.1f}%/min | ETA: {eta:.1f} min")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        count, coverage = get_status()
        print(f"Final: {count:,} LocationGroups ({coverage:.1f}% coverage)")