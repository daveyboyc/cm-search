#!/usr/bin/env python3
"""
Fix dropdown scrolling issues on technology-map and company-map pages.

This script patches the filter_bar_map.html template to fix dropdown scrolling
by removing preventDefault() from wheel events and adjusting CSS.
"""

import os
import re
from pathlib import Path

def fix_filter_bar_map():
    """Fix the dropdown scrolling in filter_bar_map.html"""
    
    template_path = Path("checker/templates/checker/includes/filter_bar_map.html")
    
    if not template_path.exists():
        print(f"Error: {template_path} not found!")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Change wheel event handler to not prevent default
    # Find the wheel event listener and modify it
    original_wheel_handler = """dropdown.addEventListener('wheel', function(e) {
            console.log('Wheel event on map dropdown', index);
            e.stopPropagation();
            e.preventDefault();
        }, { passive: false });"""
    
    fixed_wheel_handler = """dropdown.addEventListener('wheel', function(e) {
            console.log('Wheel event on map dropdown', index);
            e.stopPropagation();
            // Don't prevent default - allow natural scrolling
        }, { passive: true });"""
    
    content = content.replace(original_wheel_handler, fixed_wheel_handler)
    
    # Fix 2: Add z-index to dropdown menus to ensure they're above containers
    # Find the CSS section and add z-index
    css_addition = """
/* Fix dropdown z-index for map pages */
.filter-bar-map .dropdown-menu {
    z-index: 1200 !important; /* Above map containers */
    position: absolute !important;
}

/* Ensure dropdown container allows overflow */
.filter-bar-map .dropdown {
    position: static !important; /* Allow dropdown to escape container */
}
"""
    
    # Insert before the closing </style> tag
    content = content.replace("</style>", css_addition + "\n</style>")
    
    # Fix 3: Update the scrollable dropdown CSS to ensure proper behavior
    original_scrollable_css = """.filter-bar-map .dropdown-menu-scrollable {
    max-height: 320px !important;
    overflow-y: scroll !important;
    overflow-x: hidden !important;
    /* Ensure proper scrolling on all devices */
    -webkit-overflow-scrolling: touch !important;
    /* Prevent parent scrolling */
    overscroll-behavior: contain !important;"""
    
    fixed_scrollable_css = """.filter-bar-map .dropdown-menu-scrollable {
    max-height: 320px !important;
    overflow-y: auto !important; /* Use auto instead of scroll */
    overflow-x: hidden !important;
    /* Ensure proper scrolling on all devices */
    -webkit-overflow-scrolling: touch !important;
    /* Prevent parent scrolling */
    overscroll-behavior: contain !important;
    /* Fix for technology-map pages */
    position: relative !important;
    transform: translateZ(0) !important; /* Force GPU acceleration */"""
    
    content = content.replace(original_scrollable_css, fixed_scrollable_css)
    
    # Write the fixed content back
    with open(template_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {template_path}")
    return True

def fix_technology_map_styles():
    """Add specific fixes to technology map pages"""
    
    templates = [
        "checker/templates/checker/search_technology_map.html",
        "checker/templates/checker/search_company_map.html"
    ]
    
    css_fix = """
    /* Fix for dropdown scrolling on map pages */
    .search-results-container .dropdown-menu {
        z-index: 1200 !important;
        max-height: 320px !important;
        overflow-y: auto !important;
    }
    
    /* Ensure dropdowns can overflow their containers */
    .search-results-container .dropdown {
        position: static !important;
    }
    
    /* Fix for filter bar positioning */
    .filter-bar-map {
        position: relative !important;
        z-index: 10 !important;
    }
"""
    
    for template_path in templates:
        path = Path(template_path)
        if not path.exists():
            print(f"Warning: {template_path} not found, skipping...")
            continue
            
        with open(path, 'r') as f:
            content = f.read()
        
        # Check if fix already applied
        if "Fix for dropdown scrolling on map pages" in content:
            print(f"⏭️  {template_path} already fixed, skipping...")
            continue
        
        # Find the closing </style> tag in the template and insert our fix
        if "</style>" in content:
            # Find the last </style> tag before the {% endblock %}
            style_end = content.rfind("</style>", 0, content.find("{% endblock"))
            if style_end != -1:
                content = content[:style_end] + css_fix + "\n" + content[style_end:]
                
                with open(path, 'w') as f:
                    f.write(content)
                
                print(f"✅ Fixed {template_path}")
            else:
                print(f"❌ Could not find appropriate </style> tag in {template_path}")
        else:
            print(f"❌ No </style> tag found in {template_path}")

def main():
    """Main function to apply all fixes"""
    
    print("🔧 Fixing dropdown scrolling issues on map pages...\n")
    
    # Fix the filter bar map template
    if fix_filter_bar_map():
        print("✅ Filter bar map template fixed")
    
    # Fix the technology/company map page styles
    fix_technology_map_styles()
    
    print("\n✨ Dropdown scrolling fixes applied!")
    print("\n📝 Next steps:")
    print("1. Clear browser cache")
    print("2. Restart the development server")
    print("3. Test dropdown scrolling on technology-map pages")

if __name__ == "__main__":
    main()