# AdSense Placement Guide

## Overview
This guide documents all available ad placement templates and their recommended usage across the Capacity Market Registry site.

## Ad Placement Templates

### 1. Search Results Ads
#### `search_inline` - Inline Search Results
- **Location**: Between search results (every 5th result)
- **Usage**: `{% show_ad 'search_inline' %}`
- **Template**: `ads/search_inline.html`
- **Best For**: High engagement, contextual to user searches
- **Format**: Native-style ad that blends with search results

#### `list_bottom` - End of Search Results
- **Location**: After all search results, before pagination
- **Usage**: `{% show_list_bottom_ad %}`
- **Template**: `ads/list_bottom.html`
- **Best For**: Users who scrolled through all results
- **Format**: Banner-style, 728x90 or responsive

### 2. Header/Banner Ads
#### `header_banner` - Page Header
- **Location**: Top of main content area, below navigation
- **Usage**: `{% show_header_ad %}`
- **Template**: `ads/header_banner.html`
- **Best For**: Maximum visibility, immediate impression
- **Format**: 728x90 leaderboard or responsive

#### `banner_top` - Legacy Top Banner
- **Location**: Configurable top banner placement
- **Usage**: `{% show_ad 'banner_top' %}`
- **Template**: `ads/banner_top.html`
- **Best For**: Flexible banner placement
- **Format**: Various banner sizes

### 3. Page-Specific Ads
#### `technology_detail` - Technology Pages
- **Location**: Between sections on technology detail pages
- **Usage**: `{% show_technology_ad %}`
- **Template**: `ads/technology_detail.html`
- **Best For**: Users researching specific technologies
- **Format**: In-article style, fluid/responsive

#### `company_detail` - Company Pages
- **Location**: Between sections on company detail pages
- **Usage**: `{% show_company_ad %}`
- **Template**: `ads/company_detail.html`
- **Best For**: Users researching specific companies
- **Format**: In-article style, fluid/responsive

### 4. Layout-Based Ads
#### `sidebar_banner` - Desktop Sidebar
- **Location**: Right sidebar (desktop only)
- **Usage**: `{% show_sidebar_ad %}`
- **Template**: `ads/sidebar_banner.html`
- **Best For**: Persistent visibility during browsing
- **Format**: 300x250 rectangle or 300x600 half-page
- **Notes**: Hidden on mobile (`d-none d-lg-block`)

#### `mobile_banner` - Mobile Optimized
- **Location**: Mobile-specific banner placement
- **Usage**: `{% show_mobile_ad %}`
- **Template**: `ads/mobile_banner.html`
- **Best For**: Mobile users
- **Format**: Responsive, mobile-optimized
- **Notes**: Only shown on mobile (`d-block d-lg-none`)

#### `footer_banner` - Page Footer
- **Location**: Bottom of page content, before site footer
- **Usage**: `{% show_footer_ad %}`
- **Template**: `ads/footer_banner.html`
- **Best For**: End-of-session impression
- **Format**: 728x90 leaderboard or responsive

### 5. Special Context Ads
#### `map_overlay` - Map Interface
- **Location**: Overlay on map interfaces
- **Usage**: `{% show_ad 'map_overlay' %}`
- **Template**: `ads/map_overlay.html`
- **Best For**: Map page users
- **Format**: Overlay or sidebar on map pages

#### `list_inline` - General List Content
- **Location**: Within list content (configurable frequency)
- **Usage**: `{% show_ad 'list_inline' %}`
- **Template**: `ads/list_inline.html`
- **Best For**: Long lists and paginated content
- **Format**: Native-style, blends with list items

## Template Tag Reference

### Basic Ad Display
```django
{% load ad_tags %}
{% show_ad 'placement_name' %}
```

### Convenience Tags
```django
{% load ad_tags %}

<!-- Header/Banner Ads -->
{% show_header_ad %}
{% show_footer_ad %}

<!-- Layout-Specific -->
{% show_sidebar_ad %}    <!-- Desktop only -->
{% show_mobile_ad %}     <!-- Mobile only -->

<!-- Page-Specific -->
{% show_technology_ad %}
{% show_company_ad %}

<!-- List/Search -->
{% show_list_bottom_ad %}
```

### Inline Ad Frequency Check
```django
{% load ad_tags %}

{% for item in items %}
    <!-- Show ad every 5 items (but not first) -->
    {% if forloop.counter0|ad_frequency_check:5 %}
        {% show_ad 'search_inline' %}
    {% endif %}
    
    <!-- Your content here -->
{% endfor %}
```

### AdSense Head Script
```django
{% load ad_tags %}
{% adsense_head_script %}
```

## Ad Placement Configuration

### Database Setup
Each ad placement requires an `AdPlacement` record with:
- `name`: Template placement name (e.g., 'header_banner')
- `placement_type`: Template file name (e.g., 'header_banner')
- `ad_unit_id`: Google AdSense ad unit ID
- `size`: Ad dimensions (e.g., '728x90', 'responsive')
- `is_active`: Enable/disable the placement
- Page visibility flags: `show_on_search`, `show_on_map`, `show_on_list`, `show_on_detail`

### Example Management Command
```python
# ads/management/commands/setup_placements.py
from ads.models import AdPlacement

# Create header banner placement
AdPlacement.objects.get_or_create(
    name='header_banner',
    defaults={
        'placement_type': 'header_banner',
        'ad_unit_id': '',  # Set in production
        'size': 'responsive',
        'is_active': True,
        'show_on_search': True,
        'show_on_map': True,
        'show_on_list': True,
        'show_on_detail': True,
    }
)
```

## User Targeting

### Who Sees Ads
- ✅ Anonymous/guest users
- ✅ Trial users (free access not expired)
- ✅ Paid users who chose "show ads" preference
- ❌ Paid users (default)
- ❌ Paid users who chose "hide ads" preference  
- ❌ Staff/admin users

### Ad Preference Options
- `default`: Follow subscription status (paid users don't see ads)
- `show`: Always show ads (support the site)
- `hide`: Never show ads (paid users only)

## Performance Considerations

### Loading Strategy
1. AdSense head script loads only for users who should see ads
2. Ad containers have fallback content for testing
3. Ads load asynchronously to avoid blocking page render
4. Mobile/desktop ads are conditionally loaded via CSS classes

### Fallback Content
Each ad template includes test content that:
- Matches the visual style of real ads
- Provides energy/capacity market relevant content
- Helps with layout testing during development
- Displays when `ADSENSE_ENABLED=False` or no ad unit ID

## Testing

### Local Development
```bash
# Enable ads for testing
export ADSENSE_ENABLED=true
export ADSENSE_CLIENT_ID=ca-pub-test
export ADSENSE_TEST_MODE=true

# Disable ads
export ADSENSE_ENABLED=false
```

### Staging/Production
- Set real AdSense client ID and ad unit IDs
- Set `ADSENSE_TEST_MODE=false` in production
- Monitor ad performance and user experience
- A/B test different placements and frequencies

## Best Practices

### Placement Strategy
1. **Above the fold**: Header banners for immediate visibility
2. **Content integration**: In-article ads for engaged users
3. **Exit intent**: Footer and list-bottom ads for departing users
4. **Persistent**: Sidebar ads for continued exposure
5. **Mobile-first**: Responsive designs for all screen sizes

### User Experience
- Clearly label ads as "Advertisement" or "Ad"
- Ensure ads don't interfere with core functionality
- Respect user preferences (paid users, ad preferences)
- Use native styling that complements site design
- Avoid overly aggressive placement that hurts UX

### Revenue Optimization
- Test different ad sizes and formats
- Monitor click-through rates by placement
- Adjust frequency based on performance
- Consider user journey and engagement patterns
- Balance ad revenue with user experience

## Future Enhancements

### Planned Features
- A/B testing framework for ad placements
- User-specific ad frequency capping
- Geographic targeting for relevant ads
- Performance analytics dashboard
- Dynamic ad sizing based on content

### Integration Ideas
- Contextual ads based on search terms
- Industry-specific ad content
- Seasonal campaigns (auction periods)
- Partnership opportunities with energy companies