#!/bin/bash
# Monitor Django logs in real-time to see performance

echo "📊 MONITORING PERFORMANCE LOGS"
echo "============================="
echo ""
echo "🔍 Watch for these key indicators:"
echo "  - '✅ FAST:' = Using optimized static files"
echo "  - 'appears to be an outcode' = Postcode detected"
echo "  - 'Found X postcodes for partial match' = Location search"
echo "  - Time measurements in logs"
echo ""
echo "👉 Now go test searches at http://localhost:8000"
echo "   Try: SW11, grid, battery, nottingham"
echo ""
echo "📊 Real-time logs:"
echo "-----------------"

# Follow the Django server output
tail -f /var/log/django.log 2>/dev/null || echo "Note: Django logs are displayed in the terminal where the server is running"