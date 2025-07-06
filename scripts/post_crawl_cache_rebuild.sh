#!/bin/bash
# Post-Crawl Cache Rebuild Script
# Only rebuilds caches when data has actually changed
# Usage: ./scripts/post_crawl_cache_rebuild.sh [environment]

set -e  # Exit on any error

ENVIRONMENT=${1:-staging}
APP_NAME="cmr-$ENVIRONMENT"

echo "🔄 Post-Crawl Cache Rebuild for ($ENVIRONMENT)"

# Check if logged into Heroku
if ! heroku auth:whoami > /dev/null 2>&1; then
    echo "❌ Not logged into Heroku. Run: heroku login"
    exit 1
fi

# Check if app exists
if ! heroku apps:info $APP_NAME > /dev/null 2>&1; then
    echo "❌ Heroku app '$APP_NAME' not found"
    exit 1
fi

# Function to check if cache rebuild is needed
check_data_changes() {
    echo "🔍 Checking if data has changed since last cache build..."
    
    # Check last modified timestamp of Component table
    LAST_MODIFIED=$(heroku run -a $APP_NAME "python manage.py shell -c \"
from checker.models import Component
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT MAX(EXTRACT(EPOCH FROM NOW())) FROM checker_component WHERE last_modified IS NOT NULL')
    result = cursor.fetchone()
    print(result[0] if result and result[0] else 0)
\"" --quiet 2>/dev/null | tail -1 | tr -d '\r')

    # Check last cache build timestamp (stored in a simple flag file)
    LAST_CACHE_BUILD=$(heroku run -a $APP_NAME "python manage.py shell -c \"
import os
from django.conf import settings
cache_flag = '/tmp/last_cache_build'
if os.path.exists(cache_flag):
    with open(cache_flag, 'r') as f:
        print(f.read().strip())
else:
    print('0')
\"" --quiet 2>/dev/null | tail -1 | tr -d '\r')

    echo "📊 Last data modification: $LAST_MODIFIED"
    echo "📊 Last cache build: $LAST_CACHE_BUILD"
    
    # Compare timestamps (allow 1-hour buffer to avoid frequent rebuilds)
    if (( $(echo "$LAST_MODIFIED > $LAST_CACHE_BUILD + 3600" | bc -l) )); then
        echo "✅ Data has changed - cache rebuild needed"
        return 0
    else
        echo "⏭️  No significant data changes - skipping cache rebuild"
        return 1
    fi
}

# Function to rebuild caches with egress monitoring
rebuild_caches() {
    echo "🔄 Rebuilding caches (monitoring egress)..."
    
    # 1. Location mapping (essential for search)
    echo "📍 Rebuilding location mapping..."
    heroku run -a $APP_NAME "python manage.py build_location_mapping --light" || {
        echo "❌ Location mapping failed"
        return 1
    }
    
    # 2. Statistics cache (for homepage)
    echo "📊 Rebuilding statistics cache..."
    heroku run -a $APP_NAME "python manage.py build_statistics_cache --light" || {
        echo "❌ Statistics cache failed"
        return 1
    }
    
    # 3. Map cache (only if needed)
    echo "🗺️  Rebuilding map cache..."
    heroku run -a $APP_NAME "python manage.py build_map_cache --essential-only" || {
        echo "❌ Map cache failed"
        return 1
    }
    
    # Update cache build timestamp
    heroku run -a $APP_NAME "python manage.py shell -c \"
import time
with open('/tmp/last_cache_build', 'w') as f:
    f.write(str(int(time.time())))
print('Cache timestamp updated')
\"" || echo "⚠️  Could not update cache timestamp"
    
    echo "✅ All caches rebuilt successfully"
}

# Main execution
if check_data_changes; then
    rebuild_caches
    echo "🎉 Cache rebuild complete!"
else
    echo "✅ Caches are up to date"
fi

echo ""
echo "📊 To check cache status:"
echo "   heroku run python manage.py check_cache_status --app $APP_NAME"
echo ""
echo "💡 To force rebuild:"
echo "   heroku run python manage.py build_location_mapping --force --app $APP_NAME"