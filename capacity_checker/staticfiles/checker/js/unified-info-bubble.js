/**
 * Unified info bubble content generator for all map types
 * Creates consistent info window content across different map views
 */

function createUnifiedInfoBubbleContent(data) {
    console.log('🟢 Using unified info bubble function', data);
    
    // Determine if this is grouped data or single component
    const isGroup = data.is_group || (data.components_at_location && data.components_at_location.length > 1);
    const componentCount = data.component_count || (data.components_at_location ? data.components_at_location.length : 1);
    
    // Start building content
    let content = `<div style="max-width: 300px;">`;
    
    // Title (location name)
    content += `<h5>${data.title || data.location || 'Unknown Location'}</h5>`;
    
    // Alert for multiple components
    if (isGroup && componentCount > 1) {
        content += `<div class="alert alert-info py-1 px-2 mb-2" style="font-size: 0.85rem;">
            This location has ${componentCount} components across multiple auction years.
        </div>`;
    }
    
    // Company
    if (data.company || data.company_name) {
        const company = data.company || data.company_name;
        content += `<p><strong>Company:</strong> ${company}</p>`;
    }
    
    // Technology
    if (data.technology) {
        content += `<p><strong>Technology:</strong> ${data.technology}</p>`;
    }
    
    // CMU ID - use the newest if multiple components
    let cmuId = data.cmu_id;
    if (data.components_at_location && data.components_at_location.length > 0) {
        // Get from newest component
        const sorted = [...data.components_at_location].sort((a, b) => {
            const yearA = parseInt(a.delivery_year) || 0;
            const yearB = parseInt(b.delivery_year) || 0;
            return yearB - yearA;
        });
        cmuId = sorted[0].cmu_id || data.cmu_id;
    }
    if (cmuId) {
        content += `<p><strong>CMU ID:</strong> ${cmuId}</p>`;
    }
    
    // Auction year - extract clean year range
    let displayYear = '';
    
    // Check various possible sources for year data
    if (data.all_years && data.all_years.length > 0) {
        // From search results map format
        const firstYear = data.all_years[0];
        const yearMatch = firstYear.match(/^\d{4}-\d{2}/);
        displayYear = yearMatch ? yearMatch[0] : firstYear;
    } else if (data.components_at_location && data.components_at_location.length > 0) {
        // From main map format - get newest
        const sorted = [...data.components_at_location].sort((a, b) => {
            const yearA = parseInt(a.delivery_year) || 0;
            const yearB = parseInt(b.delivery_year) || 0;
            return yearB - yearA;
        });
        const newest = sorted[0];
        if (newest.auction_name) {
            const yearMatch = newest.auction_name.match(/^\d{4}-\d{2}/);
            displayYear = yearMatch ? yearMatch[0] : newest.auction_name;
        } else if (newest.delivery_year) {
            displayYear = newest.delivery_year;
        }
    } else if (data.auction_name) {
        // Single component with auction_name
        const yearMatch = data.auction_name.match(/^\d{4}-\d{2}/);
        displayYear = yearMatch ? yearMatch[0] : data.auction_name;
    } else if (data.delivery_year) {
        // Fallback to delivery_year
        displayYear = data.delivery_year;
    }
    
    if (displayYear) {
        content += `<p><strong>Auction:</strong> ${displayYear}</p>`;
    }
    
    // View Location Details button
    const locationName = data.title || data.location || 'Unknown Location';
    content += `<a href="/location/by-name/${encodeURIComponent(locationName)}/" class="btn btn-sm btn-primary mt-2" target="_blank">
        View Location Details
    </a>`;
    
    content += `</div>`;
    
    return content;
}