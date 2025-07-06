# Navigation Structure Documentation

## Overview
The CMR (Capacity Market Registry) application has two distinct navigation systems:

1. **Homepage Navigation** - Simple, clean interface for the main search page
2. **Universal Navigation** - Comprehensive navigation bar for all other pages

## Homepage Navigation (`/`)

### Template: `checker/templates/checker/search.html`

The homepage has its own dedicated navigation structure:

**Features:**
- Large "Capacity Market Search" title and logo
- Dedicated search bar (homepage-specific)
- Hamburger menu (from base template) in top-right corner
- No universal navbar - keeps the clean, Google-like interface
- Explanatory bubbles and "Buy Me a Coffee" button

**Navigation Elements:**
- **Search Bar**: Main search functionality for the homepage
- **Hamburger Menu**: Mobile-friendly menu in base template (`base.html` lines 594-667)
  - Home, Technologies, Companies, Locations, Map Explorer
  - User authentication (Login/Register or Account/Logout)
  - Theme toggle (Light/Dark/Auto)
  - Help modal trigger

**Key Implementation Details:**
- Extends `base.html` but excludes universal navbar
- Uses `{% block body_class %}search-page{% endblock %}` (no `has-universal-navbar` class)
- Navigation handled by base template's hamburger menu system

## Universal Navigation (All Other Pages)

### Template: `checker/templates/checker/includes/universal_navbar.html`

Used on all pages except the homepage:

**Features:**
- Fixed navigation bar at top of page
- Logo and brand name (hidden on mobile)
- Universal search bar (different from homepage search)
- Hamburger menu (Bootstrap offcanvas)

**Navigation Elements:**
- **Logo/Brand**: Links back to homepage
- **Search Bar**: Universal search functionality
- **Hamburger Menu**: Comprehensive site navigation
  - All main sections (Home, Technologies, Companies, etc.)
  - User account management
  - Theme selection
  - Help system

**Styling:**
- Fixed position at top of viewport
- Responsive design with mobile optimizations
- Theme-aware styling (light/dark mode support)
- Adds appropriate spacing to page content

## Key Differences

| Feature | Homepage | Universal Navigation |
|---------|----------|---------------------|
| Search Bar | Large, centered, Google-like | Compact, in navbar |
| Navigation | Hamburger menu only | Full navbar + hamburger |
| Positioning | Integrated in page flow | Fixed at top |
| Branding | Large logo and title | Small logo in navbar |
| Theme | Clean, minimal | Comprehensive |

## Implementation Notes

### Homepage Changes (Recent)
- **Removed**: Universal navbar include from homepage
- **Retained**: Base template hamburger menu for mobile navigation
- **Result**: Clean homepage with dedicated search + mobile-friendly navigation

### File Structure
```
templates/
├── checker/
│   ├── base.html                           # Base template with hamburger menu
│   ├── search.html                         # Homepage template
│   └── includes/
│       ├── universal_navbar.html           # Universal navigation bar
│       └── welcome_notice.html             # User welcome messages
```

### CSS Classes
- `has-universal-navbar`: Applied to pages using universal navigation
- `search-page`: Applied to homepage (no universal navbar)
- `universal-navbar`: Styling for the universal navigation bar

## Testing
- Homepage loads correctly without universal navbar
- Hamburger menu functions properly on homepage
- Search functionality works on both homepage and universal navbar
- Theme switching works across both navigation systems

## Future Considerations
- Keep homepage navigation simple and focused
- Universal navbar should remain comprehensive for site-wide navigation
- Consider user experience when adding new navigation elements
- Maintain mobile responsiveness across both systems