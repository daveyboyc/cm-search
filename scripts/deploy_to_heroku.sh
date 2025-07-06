#!/bin/bash
# CMR Heroku Deployment Script
# Usage: ./scripts/deploy_to_heroku.sh [environment]

set -e  # Exit on any error

ENVIRONMENT=${1:-staging}
APP_NAME="cmr-$ENVIRONMENT"

echo "🚀 Deploying CMR to Heroku ($ENVIRONMENT)"

# Pre-deployment checks
echo "📋 Pre-deployment checks..."

# Check if logged into Heroku
if ! heroku auth:whoami > /dev/null 2>&1; then
    echo "❌ Not logged into Heroku. Run: heroku login"
    exit 1
fi

# Check if app exists
if ! heroku apps:info $APP_NAME > /dev/null 2>&1; then
    echo "❌ Heroku app '$APP_NAME' not found. Create it first:"
    echo "   heroku create $APP_NAME"
    exit 1
fi

# Backup current data (if production)
if [ "$ENVIRONMENT" = "production" ]; then
    echo "💾 Backing up production data..."
    heroku pg:backups:capture --app $APP_NAME
    echo "✅ Backup created"
fi

# Deploy code
echo "📦 Deploying code..."
git push heroku main

# Set essential environment variables
echo "⚙️  Configuring environment..."

# Database (should already be set)
# heroku config:set DATABASE_URL="..." --app $APP_NAME

# API Keys
heroku config:set GOOGLE_MAPS_API_KEY="$GOOGLE_MAPS_API_KEY" --app $APP_NAME

# Email settings (if configured)
if [ ! -z "$EMAIL_HOST_USER" ]; then
    heroku config:set EMAIL_HOST_USER="$EMAIL_HOST_USER" --app $APP_NAME
    heroku config:set EMAIL_HOST_PASSWORD="$EMAIL_HOST_PASSWORD" --app $APP_NAME
    heroku config:set DEFAULT_FROM_EMAIL="$DEFAULT_FROM_EMAIL" --app $APP_NAME
fi

# Alert settings (when ready)
# heroku config:set SLACK_WEBHOOK_URL="..." --app $APP_NAME
# heroku config:set ADMIN_EMAIL="admin@capacitymarket.co.uk" --app $APP_NAME

# Run migrations
echo "🔧 Running migrations..."
heroku run python manage.py migrate --app $APP_NAME

# Collect static files
echo "📁 Collecting static files..."
heroku run python manage.py collectstatic --noinput --app $APP_NAME

# REMOVED: Cache building moved to post-data-update workflow
# Cache building should happen after data changes, not code deployments
# See: post_crawl_cache_rebuild.sh for data-triggered cache updates
echo "⚠️  Cache building skipped - run manually after data updates"

# Health check
echo "🏥 Health check..."
APP_URL="https://$APP_NAME.herokuapp.com"
if curl -f -s "$APP_URL" > /dev/null; then
    echo "✅ App is responding at $APP_URL"
else
    echo "❌ App not responding. Check logs: heroku logs --tail --app $APP_NAME"
    exit 1
fi

echo "🎉 Deployment complete!"
echo "📊 App URL: $APP_URL"
echo "📝 View logs: heroku logs --tail --app $APP_NAME"

# Setup scheduler (reminder)
echo ""
echo "📅 Don't forget to configure Heroku Scheduler:"
echo "   1. heroku addons:create scheduler:standard --app $APP_NAME"
echo "   2. heroku addons:open scheduler --app $APP_NAME"
echo "   3. Add job: python manage.py check_data_freshness"
echo ""
echo "🔔 To enable automation later:"
echo "   - Configure alert webhooks"
echo "   - Test data freshness checks"
echo "   - Enable automatic updates"