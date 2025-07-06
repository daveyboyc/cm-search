# Capacity Market Search

A Django web application for searching and exploring UK Capacity Market auction data, providing interactive maps and detailed component information.

## 🚀 Current Features

- **Interactive Map View**: Real-time component visualization with clustering
- **Advanced Search**: Multi-field search across locations, companies, and technologies
- **Component Details**: Comprehensive information including capacity, auction history, and contacts
- **Company & Technology Pages**: Detailed views with geographic distribution
- **2-Tier Access System**: Free tier with trial access, premium features available
- **Responsive Design**: Mobile-optimized interface with dark/light themes

## 🏗️ Architecture Overview

### Core Models
- **Component**: Individual capacity market components with full auction data
- **LocationGroup**: Pre-aggregated location data for optimized queries  
- **CMURegistry**: Additional component metadata from CMU registry
- **UserProfile**: User management with access control

### Performance Optimizations
- **LocationGroup Model**: Pre-computed location aggregations eliminate runtime grouping
- **GIN Indexes**: PostgreSQL JSON field indexing for fast searches
- **Static JSON Files**: Location mappings moved from Redis to 3MB static files
- **Sampling Approach**: Filter building limited to 500 samples vs full datasets
- **Map Caching**: Pre-rendered technology clusters for different zoom levels

## 📊 Recent Major Optimizations (2025)

### Egress Reduction (99.7% improvement)
- **Problem**: Regular search fetching 8MB per query (16,034 rows)
- **Solution**: Sampling approach limiting to 500 rows max
- **Impact**: Reduced from 8MB → 26KB per search

### LocationGroup Architecture 
- **Replaced**: Runtime component grouping with database queries
- **Added**: Pre-computed location aggregations with JSON fields
- **Result**: 82% reduction in database egress, faster queries

### Static File Migration
- **Moved**: 71.5GB Redis location mappings to 3MB JSON files  
- **Improved**: Location lookups from 5.6s → <10ms
- **Eliminated**: Redis memory pressure and cache rebuilds

## 🛠️ Development Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Redis (for caching)
- Node.js (for map clustering)

### Installation
```bash
# Clone and setup
git clone <repository>
cd cmr
pip install -r requirements.txt

# Database setup
python manage.py migrate
python manage.py build_location_groups

# Cache setup (optional, improves performance)
python manage.py build_location_mapping
python manage.py build_cmu_cache
```

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Email (production)
MAILGUN_SMTP_SERVER=smtp.mailgun.org
MAILGUN_SMTP_LOGIN=your_login
MAILGUN_SMTP_PASSWORD=your_password

# Maps
GOOGLE_MAPS_API_KEY=your_api_key

# Redis (optional)
REDIS_URL=redis://localhost:6379
```

## 🏭 Deployment

### Heroku Deployment
```bash
# Deploy to Heroku
git push heroku main

# Run essential commands
heroku run "python manage.py migrate"
heroku run "python manage.py build_location_groups"
heroku run "python manage.py collectstatic --noinput"
```

### Static Files
- Uses WhiteNoise for static file serving
- Background images stored in `/static/images/backgrounds/`
- Favicon: Green lightning pin at `/static/images/favicon.png`

## 🔧 Key Management Commands

```bash
# Build core location data
python manage.py build_location_groups

# Update from latest data crawl  
python manage.py crawl_components
python manage.py build_location_groups --incremental

# Performance optimization
python manage.py build_cmu_cache
python manage.py build_location_mapping

# Cache management
python manage.py clear_cache
```

## 🎯 Access Control System

### Free Tier
- Component searches and basic map access
- Limited to essential features
- No registration required for basic browsing

### Trial Access (1 minute for testing)
- Full map access with all technologies
- Complete search functionality  
- Requires registration and email verification

### Premium Access
- Unlimited access to all features
- Priority support
- Payment integration via Stripe

## 📱 User Interface

### Navigation
- **Universal Navbar**: Search bar with dropdown menu
- **Mobile Support**: Hamburger menu and responsive design
- **Theme Toggle**: Light/dark mode support
- **Map Integration**: Seamless transitions between list and map views

### Search Features
- **Smart Search**: Handles postcodes, company names, locations
- **Filter Dropdowns**: Technology, company, auction year filtering
- **Sorting Options**: Location, capacity, component count, relevance
- **Pagination**: Optimized for large result sets

## 🗂️ Documentation

### Current Documentation
- `README.md` - This file (main documentation)
- `TODO.md` - Current development priorities  
- `SIMPLE_2TIER_PLAN.md` - Access control implementation
- `GPT-API-DEPLOYMENT.md` - API deployment guide

### Historical Documentation
- `docs/archive/` - Completed optimization guides and implementation notes
- Contains detailed records of major performance improvements and architectural changes
- Useful for understanding past decisions and preventing regressions

## ⚠️ Important Notes

### Performance Considerations
- **Map View**: Uses optimized caching but can be resource-intensive
- **Large Searches**: Sampling approach prevents excessive egress
- **Background Images**: Collected via collectstatic, served by WhiteNoise

### Known Limitations
- Google Maps API key required for map functionality
- Redis recommended for optimal performance (though not required)
- CloudFlare caching may require manual purging after deployments

### Security
- CSRF protection enabled
- User authentication with email verification
- Access control middleware for premium features
- No sensitive data logged or exposed

## 📈 Monitoring & Maintenance

### Performance Metrics
- Database egress tracking via logs
- Search performance timing in logs  
- Cache hit/miss monitoring
- User access level tracking

### Regular Maintenance
- Weekly data crawling and LocationGroup updates
- Monitor egress usage for cost optimization
- Clear CloudFlare cache after major deployments
- Update static file collections after UI changes

---

For implementation details of specific optimizations, see archived documentation in `docs/archive/`.