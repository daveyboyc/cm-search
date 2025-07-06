#!/bin/bash
# Build LocationGroups incrementally in small batches

cd /Users/davidcrawford/PycharmProjects/cmr
source venv/bin/activate

echo "Starting incremental LocationGroup build..."
echo "This will build in batches of 500 locations at a time."
echo "Press Ctrl+C to stop at any time."
echo ""

# Get current count
CURRENT=$(python check_status_clean.py 2>/dev/null | grep "LocationGroups:" | awk '{print $2}' | tr -d ',')
echo "Starting from: $CURRENT LocationGroups"
echo ""

# Build in increments
while true; do
    echo "Building next 500 locations..."
    python manage.py build_location_groups --limit 500 2>&1 | grep -E "(Created:|Updated:|Total:|Found|Processed)"
    
    # Check new status
    echo ""
    python check_status_clean.py 2>/dev/null
    echo ""
    
    # Check if we've reached 80% coverage
    STATUS=$(python check_status_clean.py 2>/dev/null | grep "ACTIVE")
    if [[ ! -z "$STATUS" ]]; then
        echo "🎉 LocationGroups are now ACTIVE! (80% coverage reached)"
        break
    fi
    
    # Brief pause between batches
    echo "Pausing 2 seconds before next batch..."
    sleep 2
done