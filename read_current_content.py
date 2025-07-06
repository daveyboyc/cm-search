#!/usr/bin/env python3
"""
Simple script to read all visible content from the Tableau page
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

def setup_driver():
    """Setup Chrome driver"""
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def read_all_visible_content(driver):
    """Read all visible text content from the page"""
    
    print("📖 Reading all visible content...")
    
    # Get all text content
    content_analysis = driver.execute_script("""
        var results = {
            page_title: document.title,
            body_text: document.body.innerText,
            all_text_nodes: [],
            svg_elements: [],
            marker_elements: []
        };
        
        // Get all text nodes
        var walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        var node;
        while (node = walker.nextNode()) {
            var text = node.textContent.trim();
            if (text && text.length > 2) {
                var parent = node.parentElement;
                var style = window.getComputedStyle(parent);
                
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    results.all_text_nodes.push({
                        text: text,
                        parent_tag: parent.tagName,
                        parent_class: parent.className || '',
                        parent_id: parent.id || ''
                    });
                }
            }
        }
        
        // Get SVG element info
        var svgs = document.querySelectorAll('svg');
        svgs.forEach(function(svg, index) {
            var rect = svg.getBoundingClientRect();
            if (rect.width > 50 && rect.height > 50) {
                var circles = svg.querySelectorAll('circle');
                var paths = svg.querySelectorAll('path');
                
                results.svg_elements.push({
                    index: index,
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    circles: circles.length,
                    paths: paths.length,
                    has_content: svg.textContent.trim().length > 0
                });
                
                // Check circles for potential marker data
                circles.forEach(function(circle, circleIndex) {
                    var circleRect = circle.getBoundingClientRect();
                    if (circleRect.width > 5 && circleRect.width < 50) {
                        results.marker_elements.push({
                            type: 'circle',
                            svg_index: index,
                            element_index: circleIndex,
                            x: Math.round(circleRect.left + circleRect.width/2),
                            y: Math.round(circleRect.top + circleRect.height/2),
                            radius: circle.r ? circle.r.baseVal.value : 'unknown',
                            fill: circle.getAttribute('fill') || circle.style.fill || 'no-fill',
                            class: circle.className.baseVal || circle.className || '',
                            // Try to get any associated text
                            nearby_text: ''
                        });
                    }
                });
            }
        });
        
        return results;
    """)
    
    return content_analysis

def check_iframe_content(driver):
    """Check if there's content in the iframe"""
    
    print("🖼️  Checking iframe content...")
    
    try:
        iframe = driver.find_element_by_id("primaryContent")
        driver.switch_to.frame(iframe)
        
        iframe_content = driver.execute_script("""
            return {
                title: document.title,
                body_text: document.body.innerText.substring(0, 1000),
                element_count: document.querySelectorAll('*').length,
                svg_count: document.querySelectorAll('svg').length,
                circle_count: document.querySelectorAll('circle').length,
                has_meaningful_content: document.body.innerText.length > 100
            };
        """)
        
        driver.switch_to.default_content()
        return iframe_content
        
    except Exception as e:
        print(f"   ❌ Error accessing iframe: {e}")
        driver.switch_to.default_content()
        return None

def try_basic_interactions(driver):
    """Try very basic interactions to see if anything reveals content"""
    
    print("🎯 Trying basic page interactions...")
    
    # Try clicking in different areas of the page
    basic_clicks = [
        {"x": 400, "y": 300, "description": "Center-left area"},
        {"x": 500, "y": 350, "description": "Center area"},
        {"x": 300, "y": 400, "description": "Left-center area"}
    ]
    
    interactions_content = []
    
    for click in basic_clicks:
        try:
            # Use JavaScript to click at coordinates
            content_before = driver.execute_script("return document.body.innerText.length;")
            
            driver.execute_script(f"""
                var element = document.elementFromPoint({click['x']}, {click['y']});
                if (element) {{
                    element.click();
                    // Also try mouse events
                    var event = new MouseEvent('mouseover', {{
                        bubbles: true,
                        cancelable: true,
                        clientX: {click['x']},
                        clientY: {click['y']}
                    }});
                    element.dispatchEvent(event);
                }}
            """)
            
            time.sleep(2)  # Wait for any content to appear
            
            content_after = driver.execute_script("return document.body.innerText.length;")
            
            # Check if new content appeared
            if content_after > content_before:
                new_content = driver.execute_script("""
                    // Look for any tooltip or popup content
                    var tooltips = document.querySelectorAll('[class*="tooltip"], [role="tooltip"], [style*="position: absolute"]');
                    var visible_tooltips = [];
                    
                    tooltips.forEach(function(tooltip) {
                        var style = window.getComputedStyle(tooltip);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && tooltip.textContent.trim()) {
                            visible_tooltips.push({
                                text: tooltip.textContent.trim(),
                                class: tooltip.className,
                                position: {
                                    left: tooltip.getBoundingClientRect().left,
                                    top: tooltip.getBoundingClientRect().top
                                }
                            });
                        }
                    });
                    
                    return visible_tooltips;
                """)
                
                interactions_content.append({
                    "click_location": click,
                    "content_change": content_after - content_before,
                    "new_tooltips": new_content
                })
                
                print(f"   ✅ {click['description']}: Found {len(new_content)} new tooltips!")
                for tooltip in new_content:
                    print(f"     📝 Tooltip: {tooltip['text'][:100]}...")
            
        except Exception as e:
            print(f"   ❌ Error with {click['description']}: {e}")
    
    return interactions_content

def main():
    print("🔍 Simple content reading test...")
    print("🎯 Goal: See what text content is actually available")
    
    driver = setup_driver()
    
    try:
        # Load the page
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
        print(f"📡 Loading: {url}")
        driver.get(url)
        
        # Wait for loading
        print("⏳ Waiting 30 seconds for page to load...")
        time.sleep(30)
        
        # Read all visible content
        content = read_all_visible_content(driver)
        
        print(f"\n📊 Content Analysis:")
        print(f"   Page title: {content['page_title']}")
        print(f"   Body text length: {len(content['body_text'])} characters")
        print(f"   Text nodes found: {len(content['all_text_nodes'])}")
        print(f"   SVG elements: {len(content['svg_elements'])}")
        print(f"   Potential markers: {len(content['marker_elements'])}")
        
        # Show some sample text content
        print(f"\n📝 Sample body text (first 500 chars):")
        print(content['body_text'][:500])
        
        # Show text nodes
        print(f"\n📄 Sample text nodes:")
        for i, node in enumerate(content['all_text_nodes'][:10]):
            print(f"   {i+1}. {node['parent_tag']}.{node['parent_class']}: {node['text'][:50]}...")
        
        # Show SVG info
        print(f"\n🗺️  SVG Elements:")
        for svg in content['svg_elements']:
            print(f"   SVG {svg['index']}: {svg['width']}x{svg['height']}, {svg['circles']} circles, {svg['paths']} paths")
        
        # Show markers
        print(f"\n📍 Potential Markers:")
        for marker in content['marker_elements'][:5]:
            print(f"   {marker['type']} at ({marker['x']},{marker['y']}) r={marker['radius']} fill={marker['fill']}")
        
        # Check iframe
        iframe_content = check_iframe_content(driver)
        if iframe_content:
            print(f"\n🖼️  Iframe Content:")
            print(f"   Title: {iframe_content['title']}")
            print(f"   Body text length: {len(iframe_content['body_text'])} chars")
            print(f"   Elements: {iframe_content['element_count']}")
            print(f"   SVGs: {iframe_content['svg_count']}, Circles: {iframe_content['circle_count']}")
            if iframe_content['has_meaningful_content']:
                print(f"   📝 Sample iframe text: {iframe_content['body_text'][:200]}...")
        
        # Try basic interactions
        interaction_results = try_basic_interactions(driver)
        
        # Save all results
        all_results = {
            'content_analysis': content,
            'iframe_content': iframe_content,
            'interaction_results': interaction_results
        }
        
        with open("current_content_analysis.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        
        print(f"\n💾 Saved analysis to: current_content_analysis.json")
        
        # Summary
        total_meaningful_text = len([node for node in content['all_text_nodes'] if len(node['text']) > 10])
        print(f"\n📈 Summary:")
        print(f"   Meaningful text nodes: {total_meaningful_text}")
        print(f"   Interactive elements tried: {len(interaction_results)}")
        print(f"   Tooltips found: {sum(len(r['new_tooltips']) for r in interaction_results)}")
        
        if any(len(r['new_tooltips']) > 0 for r in interaction_results):
            print("   ✅ SUCCESS: Found interactive content!")
        else:
            print("   ❌ No interactive tooltips found with basic clicks")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    main()