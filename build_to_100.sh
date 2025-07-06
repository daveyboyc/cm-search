#!/bin/bash
# Build LocationGroups to 100% completion

cd /Users/davidcrawford/PycharmProjects/cmr
source venv/bin/activate

echo "=== Building LocationGroups to 100% ==="
echo "Building in batches of 500 with 2-second breaks"
echo "Press Ctrl+C to stop"
echo ""

PREV_COUNT=0
STUCK_COUNT=0
BATCH_SIZE=500

while true; do
    # Get current coverage percentage (location coverage, not component coverage)
    COVERAGE=$(python -c "
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()
from checker.models import LocationGroup, Component
from django.db.models import Q
lg_count = LocationGroup.objects.count()
# Count unique locations that are valid (not null, empty, etc)
total_locations = Component.objects.exclude(
    Q(location__isnull=True) |
    Q(location='') |
    Q(location='None') |
    Q(location='N/A') |
    Q(location='NA') |
    Q(location__icontains='TBC') |
    Q(location__icontains='to be confirmed')
).values('location').distinct().count()
coverage = (lg_count / total_locations * 100) if total_locations > 0 else 0
print(f'{coverage:.1f}')
" 2>/dev/null)
    
    # Get current count
    COUNT=$(python -c "
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()
from checker.models import LocationGroup
print(LocationGroup.objects.count())
" 2>/dev/null)
    
    echo "LocationGroups: $COUNT"
    echo "Coverage: $COVERAGE%"
    
    # Check if we've reached 99.5% (close enough to 100%)
    if (( $(echo "$COVERAGE >= 99.5" | bc -l) )); then
        echo ""
        echo "✅ LocationGroups build complete! ($COVERAGE%)"
        break
    fi
    
    # Check if we're stuck
    if [ "$COUNT" -eq "$PREV_COUNT" ]; then
        STUCK_COUNT=$((STUCK_COUNT + 1))
        if [ $STUCK_COUNT -ge 3 ]; then
            echo "⚠️  Progress seems stuck. Increasing batch size..."
            BATCH_SIZE=$((BATCH_SIZE * 2))
            STUCK_COUNT=0
        fi
    else
        STUCK_COUNT=0
        PREV_COUNT=$COUNT
    fi
    
    # Build next batch
    echo "Building next $BATCH_SIZE..."
    # Run command and capture output
    OUTPUT=$(python manage.py build_location_groups_incremental --batch $BATCH_SIZE 2>&1)
    
    # Show relevant lines or error if something went wrong
    if echo "$OUTPUT" | grep -q "Created:"; then
        echo "$OUTPUT" | grep -E "(Created:|Total LocationGroups:|Component coverage:|Completed in)" | tail -4
    else
        # Show last few lines if no normal output
        echo "$OUTPUT" | tail -5
    fi
    
    # Brief pause
    echo "Sleeping 2s..."
    sleep 2
    echo ""
done

echo ""
echo "Final status:"
python check_locationgroup_status.py