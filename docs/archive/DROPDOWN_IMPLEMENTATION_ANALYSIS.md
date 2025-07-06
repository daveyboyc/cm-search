# Dropdown Implementation Analysis: Technology-Map vs Regular Pages

## Overview
This document analyzes the differences in how dropdowns are implemented between technology-map pages and regular search pages in the CMR application.

## Bootstrap Version
- **Version Used**: Bootstrap 5.3.3 (confirmed in base.html)
- All pages use the same Bootstrap version via CDN

## Key Findings

### 1. Filter Bar Templates

#### Regular Pages (filter_bar.html)
- Uses `.dropdown-menu-scrollable` class for dropdown menus
- Includes JavaScript to handle scroll events:
  ```javascript
  dropdown.addEventListener('wheel', function(e) {
      e.stopPropagation();
      e.preventDefault();
  }, { passive: false });
  ```
- Applied to ALL `.dropdown-menu` elements, not just scrollable ones
- Max-height: 320px with overflow-y: scroll

#### Map Pages (filter_bar_map.html)
- Also uses `.dropdown-menu-scrollable` class
- Has nearly identical JavaScript scroll handling
- Uses scoped CSS with `.filter-bar-map` prefix
- Same max-height and overflow settings

### 2. Potential Issues Identified

#### Issue 1: Event Handler Conflicts
Both filter bars attach wheel event listeners that call `preventDefault()`. This could be causing issues with dropdown scrolling on technology-map pages.

#### Issue 2: CSS Scoping
- Regular filter bar: `.dropdown-menu-scrollable`
- Map filter bar: `.filter-bar-map .dropdown-menu-scrollable`

The map version has more specific CSS selectors which might not be applying correctly if the parent container structure differs.

#### Issue 3: Container Structure
Technology-map pages have a complex layout with:
- Fixed positioning on main container
- Split-screen layout (60% results, 40% map)
- Overflow settings on parent containers that might interfere

### 3. Specific Differences in Technology-Map Pages

1. **Override Styles**: Technology-map pages have extensive CSS overrides:
   ```css
   html, body {
       overflow: hidden !important;
   }
   .main-container {
       position: fixed !important;
       z-index: 1000 !important;
   }
   ```

2. **Z-index Layering**: Multiple z-index values that could affect dropdown stacking:
   - `.main-container`: z-index: 1000
   - `.search-results-container`: z-index: 1001
   - `.map-container`: z-index: 1001

3. **Custom Dropdown Styling**: Technology-map pages add their own dropdown styles:
   ```css
   .dropdown-menu {
       border-radius: 8px;
       box-shadow: 0 4px 12px rgba(0,0,0,0.1);
   }
   ```

### 4. JavaScript Event Handling Differences

The technology-map page has additional JavaScript that might interfere:
- Scroll management for search results container
- Map interaction handlers
- Theme switching functionality

## Recommendations for Fixing

### 1. Fix Event Handler Conflicts
Remove or modify the `preventDefault()` on wheel events in the filter bar JavaScript. Instead, only stop propagation:
```javascript
dropdown.addEventListener('wheel', function(e) {
    e.stopPropagation();
    // Remove e.preventDefault() to allow dropdown scrolling
}, { passive: true });
```

### 2. Ensure Proper Z-index Stacking
Add explicit z-index to dropdown menus in technology-map pages:
```css
.search-results-container .dropdown-menu {
    z-index: 1100 !important; /* Higher than container */
}
```

### 3. Fix Overflow Issues
The `overflow: hidden` on body/html might be preventing dropdown scrolling. Consider:
```css
.search-results-container {
    overflow-y: auto !important;
    overflow-x: visible !important; /* Allow dropdowns to overflow horizontally */
}
```

### 4. Simplify Event Handlers
Instead of applying scroll handlers to all dropdowns, target only the specific scrollable areas within dropdowns.

### 5. Test Bootstrap Dropdown Data Attributes
Ensure all dropdown triggers have proper Bootstrap 5 attributes:
- `data-bs-toggle="dropdown"`
- `data-bs-auto-close="outside"` (if needed)

## Conclusion

The main issues appear to be:
1. **preventDefault() on wheel events** blocking dropdown scrolling
2. **CSS overflow and positioning conflicts** from the fixed layout
3. **Z-index stacking issues** between containers and dropdowns

The dropdowns work on regular pages because they don't have the complex fixed positioning and overflow constraints that the map pages have.