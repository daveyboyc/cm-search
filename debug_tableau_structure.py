#!/usr/bin/env python3
"""
Debug script to analyze Tableau page structure and find map markers
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import json
import time
import re

def setup_driver():
    """Setup Chrome driver"""
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def comprehensive_page_analysis(driver):
    """Perform comprehensive analysis of the Tableau page structure"""
    
    print("🔍 Starting comprehensive page analysis...")
    
    # 1. Basic page info
    page_info = driver.execute_script("""
        return {
            title: document.title,
            url: window.location.href,
            readyState: document.readyState,
            body_classes: document.body.className,
            total_elements: document.querySelectorAll('*').length
        };
    """)
    
    print(f"📄 Page Info:")
    print(f"   Title: {page_info['title']}")
    print(f"   URL: {page_info['url']}")
    print(f"   Ready State: {page_info['readyState']}")
    print(f"   Total Elements: {page_info['total_elements']}")
    
    # 2. Find all iframes (Tableau often uses iframes)
    iframes = driver.execute_script("""
        var iframes = document.querySelectorAll('iframe');
        var frameInfo = [];
        
        for (var i = 0; i < iframes.length; i++) {
            var frame = iframes[i];
            var rect = frame.getBoundingClientRect();
            frameInfo.push({
                index: i,
                src: frame.src || 'no-src',
                id: frame.id || 'no-id',
                className: frame.className || 'no-class',
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                left: Math.round(rect.left),
                top: Math.round(rect.top)
            });
        }
        
        return frameInfo;
    """)
    
    print(f"\n🖼️  Found {len(iframes)} iframes:")
    for iframe in iframes:
        print(f"   Frame {iframe['index']}: {iframe['width']}x{iframe['height']} at ({iframe['left']},{iframe['top']})")
        print(f"     ID: {iframe['id']}, Class: {iframe['className']}")
        print(f"     Src: {iframe['src'][:100]}...")
    
    # 3. Look for Tableau-specific elements
    tableau_elements = driver.execute_script("""
        var tableau_selectors = [
            '[class*="tableau"]',
            '[class*="tab-"]',
            '[class*="viz"]',
            '[data-tab]',
            '[data-tableau]',
            'object[type="application/x-shockwave-flash"]',
            'object[data*="tableau"]'
        ];
        
        var found = [];
        tableau_selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                found.push({
                    selector: selector,
                    count: elements.length,
                    sample_classes: Array.from(elements).slice(0,3).map(el => el.className).join(', ')
                });
            }
        });
        
        return found;
    """)
    
    print(f"\n📊 Tableau Elements:")
    for element in tableau_elements:
        print(f"   {element['selector']}: {element['count']} elements")
        if element['sample_classes']:
            print(f"     Sample classes: {element['sample_classes']}")
    
    # 4. Look for SVG elements (maps often use SVG)
    svg_analysis = driver.execute_script("""
        var svgs = document.querySelectorAll('svg');
        var svg_info = [];
        
        svgs.forEach(function(svg, index) {
            var rect = svg.getBoundingClientRect();
            var circles = svg.querySelectorAll('circle').length;
            var paths = svg.querySelectorAll('path').length;
            var groups = svg.querySelectorAll('g').length;
            
            if (rect.width > 100 && rect.height > 100) {  // Only large SVGs likely to be maps
                svg_info.push({
                    index: index,
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    left: Math.round(rect.left),
                    top: Math.round(rect.top),
                    circles: circles,
                    paths: paths,
                    groups: groups,
                    id: svg.id || 'no-id',
                    className: svg.className.baseVal || svg.className || 'no-class'
                });
            }
        });
        
        return svg_info;
    """)
    
    print(f"\n🗺️  SVG Analysis ({len(svg_analysis)} large SVGs found):")
    for svg in svg_analysis:
        print(f"   SVG {svg['index']}: {svg['width']}x{svg['height']} at ({svg['left']},{svg['top']})")
        print(f"     ID: {svg['id']}, Class: {svg['className']}")
        print(f"     Contains: {svg['circles']} circles, {svg['paths']} paths, {svg['groups']} groups")
    
    # 5. Look for clickable elements in the map area
    clickable_analysis = driver.execute_script("""
        var clickables = [];
        var elements = document.querySelectorAll('*');
        
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var rect = el.getBoundingClientRect();
            
            // Look for elements in the likely map area
            if (rect.width > 5 && rect.width < 100 && 
                rect.height > 5 && rect.height < 100 &&
                rect.left > 50 && rect.left < 900 &&
                rect.top > 50 && rect.top < 700) {
                
                var style = window.getComputedStyle(el);
                var isClickable = (
                    el.onclick || 
                    style.cursor === 'pointer' || 
                    el.getAttribute('role') === 'button' ||
                    el.tagName === 'BUTTON' ||
                    el.tagName === 'A' ||
                    el.hasAttribute('data-tb-test-id') ||
                    el.hasAttribute('data-mark-type')
                );
                
                if (isClickable) {
                    clickables.push({
                        tagName: el.tagName,
                        className: el.className || '',
                        id: el.id || '',
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        cursor: style.cursor,
                        attributes: Array.from(el.attributes).map(attr => attr.name).join(',')
                    });
                }
            }
        }
        
        return clickables.slice(0, 20);  // Limit to first 20
    """)
    
    print(f"\n🖱️  Clickable Elements in Map Area ({len(clickable_analysis)} found):")
    for clickable in clickable_analysis:
        print(f"   {clickable['tagName']} at ({clickable['x']},{clickable['y']}) - {clickable['width']}x{clickable['height']}")
        print(f"     Class: {clickable['className']}, Cursor: {clickable['cursor']}")
        print(f"     Attributes: {clickable['attributes']}")
    
    return {
        'page_info': page_info,
        'iframes': iframes,
        'tableau_elements': tableau_elements,
        'svg_analysis': svg_analysis,
        'clickable_analysis': clickable_analysis
    }

def check_iframe_content(driver, iframe_index):
    """Check content inside a specific iframe"""
    print(f"\n🔍 Analyzing iframe {iframe_index}...")
    
    try:
        # Switch to iframe
        driver.switch_to.frame(iframe_index)
        
        # Analyze iframe content
        iframe_analysis = driver.execute_script("""
            return {
                title: document.title,
                url: window.location.href,
                body_classes: document.body.className,
                total_elements: document.querySelectorAll('*').length,
                svg_count: document.querySelectorAll('svg').length,
                circle_count: document.querySelectorAll('circle').length,
                path_count: document.querySelectorAll('path').length
            };
        """)
        
        print(f"   Title: {iframe_analysis['title']}")
        print(f"   Total elements: {iframe_analysis['total_elements']}")
        print(f"   SVG elements: {iframe_analysis['svg_count']}")
        print(f"   Circles: {iframe_analysis['circle_count']}")
        print(f"   Paths: {iframe_analysis['path_count']}")
        
        # Look for markers in iframe
        iframe_markers = driver.execute_script("""
            var markers = [];
            var circles = document.querySelectorAll('circle');
            
            circles.forEach(function(circle, index) {
                var rect = circle.getBoundingClientRect();
                if (rect.width > 5 && rect.width < 50) {
                    markers.push({
                        index: index,
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2),
                        radius: circle.r ? circle.r.baseVal.value : 'unknown',
                        fill: circle.getAttribute('fill') || 'no-fill',
                        className: circle.className.baseVal || circle.className || 'no-class'
                    });
                }
            });
            
            return markers.slice(0, 10);  // First 10 markers
        """)
        
        print(f"   Found {len(iframe_markers)} potential markers in iframe:")
        for marker in iframe_markers[:5]:  # Show first 5
            print(f"     Marker {marker['index']}: ({marker['x']},{marker['y']}) r={marker['radius']} fill={marker['fill']}")
        
        # Switch back to main frame
        driver.switch_to.default_content()
        
        return iframe_analysis, iframe_markers
        
    except Exception as e:
        print(f"   ❌ Error analyzing iframe {iframe_index}: {e}")
        driver.switch_to.default_content()
        return None, []

def test_marker_interaction(driver, iframe_index, marker_info):
    """Test interaction with a specific marker in an iframe"""
    print(f"\n🎯 Testing interaction with marker in iframe {iframe_index}...")
    
    try:
        # Switch to iframe
        driver.switch_to.frame(iframe_index)
        
        # Try to interact with the marker
        interaction_result = driver.execute_script("""
            var marker_x = arguments[0];
            var marker_y = arguments[1];
            
            var element = document.elementFromPoint(marker_x, marker_y);
            if (!element) return {success: false, error: 'No element found'};
            
            // Try clicking
            element.click();
            
            // Wait briefly and check for tooltips
            setTimeout(function() {
                var tooltips = document.querySelectorAll('[class*="tooltip"], [role="tooltip"]');
                console.log('Found tooltips:', tooltips.length);
            }, 1000);
            
            return {success: true, element_tag: element.tagName, element_class: element.className};
        """, marker_info['x'], marker_info['y'])
        
        # Wait for tooltip
        time.sleep(2)
        
        # Check for tooltip content
        tooltip_content = driver.execute_script("""
            var tooltips = [];
            var selectors = ['[class*="tooltip"]', '[role="tooltip"]', '.viz-tooltip'];
            
            selectors.forEach(function(selector) {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {
                    if (el.offsetParent !== null) {
                        tooltips.push({
                            selector: selector,
                            text: el.textContent.trim(),
                            visible: true
                        });
                    }
                });
            });
            
            return tooltips;
        """)
        
        print(f"   Interaction result: {interaction_result}")
        print(f"   Tooltips found: {len(tooltip_content)}")
        
        for tooltip in tooltip_content:
            print(f"     Tooltip: {tooltip['text'][:100]}...")
        
        # Switch back to main frame
        driver.switch_to.default_content()
        
        return interaction_result, tooltip_content
        
    except Exception as e:
        print(f"   ❌ Error testing marker interaction: {e}")
        driver.switch_to.default_content()
        return None, []

def main():
    print("🚀 Starting Tableau structure debug analysis...")
    
    driver = setup_driver()
    
    try:
        # Load the Tableau page
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
        print(f"📡 Loading: {url}")
        driver.get(url)
        
        # Wait for page to load
        print("⏳ Waiting for Tableau to load (30 seconds)...")
        time.sleep(30)
        
        # Take screenshot
        driver.save_screenshot("ietf_debug_capture.png")
        print("📸 Saved screenshot: ietf_debug_capture.png")
        
        # Perform comprehensive analysis
        analysis_results = comprehensive_page_analysis(driver)
        
        # Save analysis results
        with open("tableau_debug_analysis.json", "w") as f:
            json.dump(analysis_results, f, indent=2, default=str)
        print("💾 Saved analysis: tableau_debug_analysis.json")
        
        # If we found iframes, analyze their content
        if analysis_results['iframes']:
            print("\n🔍 Analyzing iframe contents...")
            
            for i, iframe in enumerate(analysis_results['iframes']):
                if iframe['width'] > 500 and iframe['height'] > 300:  # Large enough to contain a map
                    iframe_analysis, iframe_markers = check_iframe_content(driver, i)
                    
                    # If we found markers in this iframe, test interaction
                    if iframe_markers:
                        print(f"\n🎯 Testing marker interactions in iframe {i}...")
                        for marker in iframe_markers[:3]:  # Test first 3 markers
                            interaction_result, tooltip_content = test_marker_interaction(driver, i, marker)
                            
                            if tooltip_content:
                                print(f"   ✅ Found tooltip data for marker {marker['index']}!")
                                # This would be where we extract the actual project data
                                break
        
        print("\n📊 Debug Analysis Summary:")
        print(f"   Total iframes: {len(analysis_results['iframes'])}")
        print(f"   Tableau elements found: {sum(el['count'] for el in analysis_results['tableau_elements'])}")
        print(f"   Large SVGs: {len(analysis_results['svg_analysis'])}")
        print(f"   Clickable elements: {len(analysis_results['clickable_analysis'])}")
        
    except Exception as e:
        print(f"❌ Error during debug analysis: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    main()