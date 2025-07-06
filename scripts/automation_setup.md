# CMR Data Automation Setup

## Overview
This directory contains automation scripts for monitoring and updating CMR data.

## Commands Available

### 1. Data Freshness Check
```bash
# Basic check
python manage.py check_data_freshness

# With alerts (when configured)
python manage.py check_data_freshness --send-alerts

# Auto-update if needed (DANGEROUS - use with caution)
python manage.py check_data_freshness --auto-update --threshold 100
```

### 2. Full Update Pipeline
```bash
# Complete crawl + geocode + cache rebuild
python update_database.py --crawl --geocode --rebuild-caches
```

## Deployment Setup

### Local Development
```bash
# Weekly cron job (Sundays at 2 AM)
0 2 * * 0 cd /path/to/cmr && source venv/bin/activate && python manage.py check_data_freshness --send-alerts

# Monthly full update (first Sunday at 1 AM)  
0 1 1-7 * 0 cd /path/to/cmr && source venv/bin/activate && python update_database.py --full-pipeline
```

### Heroku Production
```bash
# Add scheduler addon
heroku addons:create scheduler:standard

# Configure jobs in Heroku dashboard:
# Daily: python manage.py check_data_freshness
# Weekly: python update_database.py --incremental-update
# Monthly: python update_database.py --full-pipeline
```

### Environment Variables Needed
```bash
# Heroku config
heroku config:set DATABASE_URL="postgresql://..."
heroku config:set GOOGLE_MAPS_API_KEY="..."

# Mailgun configuration
heroku config:set MAILGUN_DOMAIN="mg.capacitymarket.co.uk"
heroku config:set MAILGUN_API_KEY="key-123abc456def789..."
heroku config:set ADMIN_EMAIL="admin@capacitymarket.co.uk"
heroku config:set FROM_EMAIL="CMR System <noreply@mg.capacitymarket.co.uk>"

# Optional: Slack webhooks
heroku config:set SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

## Alert Configuration

### Mailgun Setup (Recommended)
1. **Create Mailgun account** at https://mailgun.com
2. **Add domain** (e.g., `mg.capacitymarket.co.uk`)
3. **DNS Configuration**:
   ```
   TXT  @  "v=spf1 include:mailgun.org ~all"
   TXT  mg  "k=rsa; p=YOUR_PUBLIC_KEY"
   CNAME mg.capacitymarket.co.uk mailgun.org
   ```
4. **Get API key** from Mailgun dashboard
5. **Set environment variables** (see above)

### Slack Webhooks (Optional)
1. Create Slack app at https://api.slack.com/apps
2. Add incoming webhook to your workspace
3. Set `SLACK_WEBHOOK_URL` environment variable

### Email Features
✅ **HTML emails** with styled alerts  
✅ **Crawl completion** notifications  
✅ **New data detection** alerts  
✅ **System status** summaries  
✅ **Actionable commands** in emails

## Monitoring Thresholds

| Condition | Threshold | Action |
|-----------|-----------|--------|
| New CMU IDs | 50+ | Send alert |
| New Components | 1000+ | Send alert |
| Days since update | 7+ | Warning alert |
| API connectivity | Failed | Critical alert |

## Safety Features

- **Dry run mode**: Test without making changes
- **Manual approval**: No auto-updates by default
- **Checkpoint system**: Resume interrupted crawls
- **Incremental updates**: Only process new data

## Implementation Steps (When Ready)

1. **Test locally**:
   ```bash
   python manage.py check_data_freshness --dry-run
   ```

2. **Configure alerts**:
   - Set up Slack webhook
   - Configure email settings
   - Test alert delivery

3. **Deploy to Heroku**:
   - Set environment variables
   - Add scheduler jobs
   - Test automation

4. **Monitor performance**:
   - Check logs regularly
   - Adjust thresholds as needed
   - Optimize crawl frequency

## Current Status: FRAMEWORK ONLY
⚠️  **Not yet implemented** - just the structure is in place.
Ready to activate when the main application development is complete.