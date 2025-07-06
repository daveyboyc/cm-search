# Ad Testing Templates

This directory contains standalone HTML templates for previewing how advertisements would look on your Capacity Market Search site **without affecting your live application**.

## Templates Created

### 1. `test_base_with_ads.html`
**Purpose**: General page layout with ads
**Features**:
- Top banner ad (728x90 leaderboard)
- Sidebar ad (300x250 rectangle) 
- In-content ads between sections
- Mobile banner ad (320x50)
- Footer area ad
- Responsive design that adapts to mobile

**Best for**: Testing ad placement on any regular content page

### 2. `test_homepage_ads.html`
**Purpose**: Homepage-specific ad layout
**Features**:
- Top notification bar ad
- Left/right sidebar ads (desktop only)
- Bottom section native ad
- Mobile banner ad
- Respects your unique homepage Google-like design

**Best for**: Seeing how ads would integrate with your homepage's unique navigation

### 3. `test_search_results_ads.html`
**Purpose**: Search results page with integrated ads
**Features**:
- Top banner ad
- Sidebar ad (sticky on desktop)
- Multiple inline ads between search results
- Realistic search result cards
- Pagination with ads

**Best for**: Testing ad placement in your main search functionality

### 4. `test_mobile_ads.html`
**Purpose**: Mobile-focused ad experience
**Features**:
- Simulated mobile device (375px width)
- Top banner ad with close button
- Native ads (look like content)
- Sticky bottom ad bar
- Interstitial overlay ad
- Touch-friendly interface

**Best for**: Understanding mobile ad experience and user impact

## How to Use These Templates

### Option 1: Open Directly in Browser
```bash
# Navigate to the templates directory
cd /Users/davidcrawford/PycharmProjects/cmr/checker/templates/test_ads/

# Open any template in your browser
open test_homepage_ads.html
# or
firefox test_base_with_ads.html
# or drag the file to your browser
```

### Option 2: Serve with Python (recommended)
```bash
# Navigate to the test_ads directory
cd /Users/davidcrawford/PycharmProjects/cmr/checker/templates/test_ads/

# Start a simple HTTP server
python3 -m http.server 8080

# Then visit in browser:
# http://localhost:8080/test_homepage_ads.html
# http://localhost:8080/test_base_with_ads.html
# http://localhost:8080/test_search_results_ads.html
# http://localhost:8080/test_mobile_ads.html
```

## Interactive Features

### All Templates Support:
- **Theme Toggle**: Press `T` to switch between light/dark themes
- **Clickable Elements**: All ads, buttons, and results are interactive
- **Responsive Design**: Resize browser to see mobile behavior

### Mobile Template Extras:
- **Interstitial Ad**: Press `I` to show popup ad
- **Close Buttons**: All ads can be dismissed
- **Touch-Friendly**: Optimized for mobile interaction

## Ad Types Demonstrated

### 1. **Banner Ads**
- **Leaderboard** (728x90): Top of page, high visibility
- **Mobile Banner** (320x50): Mobile-optimized top placement

### 2. **Display Ads**
- **Rectangle** (300x250): Sidebar placement, good engagement
- **Square**: Various sizes for different content areas

### 3. **Native Ads**
- **In-Content**: Styled to match your content
- **Sponsored Content**: Clearly labeled but integrated

### 4. **Mobile-Specific**
- **Sticky Bottom**: Persistent but dismissible
- **Interstitial**: Full-screen overlay (use sparingly)

## User Experience Testing

### Non-Subscriber Experience
All templates show the **NON-SUBSCRIBER** experience with full ad visibility:
- Red indicator shows "NON-SUBSCRIBER - Ads Visible"
- All ad placements are active
- Realistic ad content for energy/tech industry

### Subscriber Experience Testing
To simulate the subscriber experience:
1. Hide ads by setting `display: none` on `.ad-container` elements
2. Or modify the user status indicator to show "SUBSCRIBER"

## Ad Content Examples

The templates include realistic ad content relevant to your energy industry:
- **Battery Storage Solutions**
- **Solar Panel Installation**  
- **Smart Grid Technology**
- **Energy Trading Platforms**
- **Industrial Energy Audits**
- **Renewable Energy Marketplace**

## Technical Details

### File Dependencies
- **Bootstrap 5.3.3**: For responsive layout
- **Bootstrap Icons**: For UI elements
- **Google Fonts (Roboto)**: Matches your site font
- **No external ad scripts**: Pure CSS/HTML mockups

### Browser Compatibility
- Chrome, Firefox, Safari, Edge
- Mobile browsers (iOS Safari, Chrome Mobile)
- Responsive breakpoints: 768px, 480px

### Performance
- Lightweight: No actual ad network calls
- Fast loading: All content is local
- No tracking: Pure preview templates

## Next Steps

After reviewing these templates:

1. **Choose ad placements** you like
2. **Test user feedback** by sharing template URLs
3. **Select ad networks** (Google AdSense, Carbon Ads, etc.)
4. **Implement gradual rollout**:
   - Start with one ad placement
   - Test with non-subscribers only
   - Monitor impact on conversions
   - Gradually add more placements

## Safety Notes

⚠️ **These are TEST templates only**
- They do NOT affect your live site
- They do NOT contain real ad network code
- They do NOT track users or collect data
- They are for PREVIEW purposes only

## Questions to Consider

While reviewing these templates, consider:

1. **User Experience**: Do ads feel intrusive or helpful?
2. **Revenue vs UX**: Which placements balance income with usability?
3. **Mobile Impact**: How do ads affect mobile browsing?
4. **Content Integration**: Do native ads blend well with your content?
5. **Subscriber Value**: Do ads make subscription more appealing?

## Implementation Checklist

When ready to implement real ads:

- [ ] Choose 1-2 initial ad placements
- [ ] Sign up for ad networks (AdSense, Carbon Ads, etc.)
- [ ] Add non-subscriber detection logic
- [ ] Implement responsive ad units
- [ ] Add proper ad labeling ("Advertisement", "Sponsored")
- [ ] Test on mobile devices
- [ ] Monitor site performance impact
- [ ] Track revenue vs subscription conversions

---

**Created**: Ad testing templates for Capacity Market Search
**Purpose**: Safe preview of advertising integration options
**Status**: Ready for review and feedback