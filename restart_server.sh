#!/bin/bash
# Restart Django server with the performance fixes

echo "🔄 Restarting Django server with performance fixes..."

# Kill any existing Django server
pkill -f "manage.py runserver" 2>/dev/null || true

# Give it a moment to clean up
sleep 1

# Start the server in the background
cd /Users/davidcrawford/PycharmProjects/cmr
source venv/bin/activate

echo "🚀 Starting server..."
python manage.py runserver 8000 &

# Give it a moment to start
sleep 2

echo "✅ Server restarted!"
echo ""
echo "📊 Expected improvements:"
echo "  - 'battery' search: 4.7s → ~1s"
echo "  - Location checks: 0.5s → <10ms"
echo "  - No more 'Cache MISS for area postcodes'"
echo ""
echo "🔍 Test it now at http://localhost:8000"
echo "   Try searching for: battery, grid, SW11"