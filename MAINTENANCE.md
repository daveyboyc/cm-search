# Heroku Maintenance Mode Setup

## Quick Start

### Enable Maintenance Mode
```bash
# Enable maintenance mode with custom page
heroku maintenance:on --app neso-cmr-search

# Or with a custom page URL (after deploying)
heroku config:set MAINTENANCE_PAGE_URL=https://capacitymarket.co.uk/static/maintenance.html --app neso-cmr-search
```

### Disable Maintenance Mode
```bash
heroku maintenance:off --app neso-cmr-search
```

## What We've Created

1. **Static Maintenance Page**: `/static/maintenance.html`
   - Self-contained HTML with embedded SVG
   - Beautiful animated wind turbine
   - Uses live favicon from your site
   - Responsive design
   - No external dependencies

2. **Django Templates** (for local testing):
   - `templates/maintenance.html` - Main template
   - `templates/maintenance_svg.html` - SVG component

## Deployment Instructions

### Option 1: Commit and Push (Recommended)
```bash
# Add only the maintenance files
git add static/maintenance.html MAINTENANCE.md
git commit -m "Add custom maintenance page with animated SVG"
git push heroku trades_branch:main
```

### Option 2: Deploy Without Other Changes
If you want to deploy ONLY the maintenance page:
```bash
# Stash current changes (if any)
git stash push -m "Work in progress"

# Deploy just the maintenance page
git add static/maintenance.html
git commit -m "Add maintenance page"
git push heroku trades_branch:main

# Restore your work
git stash pop
```

## Usage

1. **Deploy the maintenance page** (push to Heroku)
2. **Enable maintenance mode**:
   ```bash
   heroku maintenance:on --app neso-cmr-search
   ```
3. When ready, **disable maintenance mode**:
   ```bash
   heroku maintenance:off --app neso-cmr-search
   ```

## Features

✅ **Animated wind turbine** - Spinning blades for visual appeal
✅ **Professional design** - Matches your site's energy theme  
✅ **Responsive layout** - Works on all devices
✅ **Self-contained** - No external dependencies
✅ **Uses live favicon** - Consistent branding
✅ **Contact information** - Includes email for urgent inquiries

## Local Testing

To test the maintenance page locally:
```bash
python manage.py toggle_maintenance on
# Visit http://localhost:8000
python manage.py toggle_maintenance off
```

## Notes

- The maintenance page uses absolute URL for favicon to ensure it works during maintenance
- Heroku's maintenance mode automatically serves the page when enabled
- No changes to your main application code needed
- Favicon and other static assets remain untouched