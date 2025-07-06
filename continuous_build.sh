#!/bin/bash
# Continuous LocationGroup builder

cd /Users/davidcrawford/PycharmProjects/cmr
source venv/bin/activate

echo "=== Continuous LocationGroup Builder ==="
echo "Building in batches of 100 with 3-second breaks"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    # Get current status
    STATUS=$(python check_status_clean.py 2>/dev/null)
    echo "$STATUS"
    
    # Check if active (look for ✅ ACTIVE, not just ACTIVE)
    if echo "$STATUS" | grep -q "✅ ACTIVE"; then
        echo ""
        echo "🎉 LocationGroups are now ACTIVE!"
        break
    fi
    
    # Build next batch
    echo "Building next 100..."
    python manage.py build_location_groups_incremental --batch 100 2>&1 | grep -E "(Created:|Total LocationGroups:|Component coverage:)" | tail -3
    
    # Brief pause
    echo "Sleeping 3s..."
    sleep 3
    echo ""
done