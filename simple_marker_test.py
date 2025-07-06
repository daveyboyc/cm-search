#!/usr/bin/env python3
"""
Simple marker test - Fix iframe access and try basic interactions
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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

def check_iframe_properly(driver):
    """Check iframe content using correct Selenium syntax"""
    
    print("🖼️  Checking iframe content (fixed syntax)...")
    
    try:
        # Use the new Selenium syntax
        iframe = driver.find_element(By.ID, "primaryContent")
        driver.switch_to.frame(iframe)
        
        iframe_content = driver.execute_script("""
            var results = {
                title: document.title,
                body_text: document.body.innerText,
                element_count: document.querySelectorAll('*').length,
                svg_count: document.querySelectorAll('svg').length,
                circle_count: document.querySelectorAll('circle').length,
                path_count: document.querySelectorAll('path').length,
                has_map_content: false
            };
            
            // Look for map-specific content
            var mapIndicators = [
                document.querySelectorAll('[class*="map"]').length,
                document.querySelectorAll('[class*="geo"]').length,
                document.querySelectorAll('[class*="marker"]').length,
                document.querySelectorAll('[class*="point"]').length
            ];
            
            results.map_indicators = mapIndicators;
            results.has_map_content = mapIndicators.some(count => count > 0);
            
            // Get any visible text in iframe
            var visibleTexts = [];
            var walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            var node;
            while (node = walker.nextNode()) {
                var text = node.textContent.trim();
                if (text && text.length > 3) {
                    visibleTexts.push(text);
                }
            }
            
            results.visible_texts = visibleTexts.slice(0, 20); // First 20 texts
            
            return results;
        """)
        
        # Get actual markers in iframe
        markers_in_iframe = driver.execute_script("""
            var markers = [];
            
            // Look for circles (common map markers)
            var circles = document.querySelectorAll('circle');
            circles.forEach(function(circle, index) {
                var rect = circle.getBoundingClientRect();
                if (rect.width > 3 && rect.width < 100) {
                    markers.push({
                        type: 'circle',
                        index: index,
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2),
                        radius: circle.r ? circle.r.baseVal.value : 'unknown',
                        fill: circle.getAttribute('fill') || 'no-fill',
                        parent_svg: circle.closest('svg') ? 'yes' : 'no'
                    });
                }
            });
            
            // Look for other potential markers
            var paths = document.querySelectorAll('path[fill]');
            paths.forEach(function(path, index) {
                var rect = path.getBoundingClientRect();
                if (rect.width > 3 && rect.width < 50 && rect.height > 3 && rect.height < 50) {
                    markers.push({
                        type: 'path',
                        index: index,
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2),
                        fill: path.getAttribute('fill') || 'no-fill',
                        parent_svg: path.closest('svg') ? 'yes' : 'no'
                    });
                }
            });
            
            return markers;
        """)
        
        driver.switch_to.default_content()
        
        print(f"   ✅ Iframe accessed successfully!")
        print(f"   Title: {iframe_content['title']}")
        print(f"   Body text length: {len(iframe_content['body_text'])} chars")
        print(f"   Elements: {iframe_content['element_count']}")
        print(f"   SVGs: {iframe_content['svg_count']}, Circles: {iframe_content['circle_count']}, Paths: {iframe_content['path_count']}")
        print(f"   Map indicators: {iframe_content['map_indicators']}")
        print(f"   Has map content: {iframe_content['has_map_content']}")
        print(f"   Markers found: {len(markers_in_iframe)}")
        
        if iframe_content['visible_texts']:
            print(f"   📝 Sample iframe texts:")
            for i, text in enumerate(iframe_content['visible_texts'][:5]):
                print(f"     {i+1}. {text[:50]}...")
        
        if markers_in_iframe:
            print(f"   📍 Sample markers:")
            for i, marker in enumerate(markers_in_iframe[:3]):
                print(f"     {i+1}. {marker['type']} at ({marker['x']},{marker['y']}) fill={marker['fill']}")
        
        return iframe_content, markers_in_iframe
        
    except Exception as e:
        print(f"   ❌ Error accessing iframe: {e}")
        driver.switch_to.default_content()
        return None, []

def test_simple_marker_clicks(driver, markers):
    """Test simple JavaScript clicks on markers"""
    
    if not markers:
        print("   ❌ No markers to test")
        return []
    
    print(f"🎯 Testing simple clicks on {len(markers)} markers...")
    
    results = []
    
    for i, marker in enumerate(markers[:3]):  # Test first 3 markers
        try:
            print(f"   Testing marker {i+1}: {marker['type']} at ({marker['x']},{marker['y']})")
            
            # Switch to iframe for interaction
            iframe = driver.find_element(By.ID, "primaryContent")
            driver.switch_to.frame(iframe)
            
            # Try clicking with JavaScript
            click_result = driver.execute_script(f"""
                var x = {marker['x']};
                var y = {marker['y']};
                
                // Get element at coordinates
                var element = document.elementFromPoint(x, y);
                if (!element) return {{success: false, error: 'No element at coordinates'}};
                
                // Store initial page text
                var initialText = document.body.innerText;
                
                // Try click
                element.click();
                
                // Wait a moment
                var start = Date.now();
                while (Date.now() - start < 1000) {{
                    // Wait 1 second
                }}
                
                // Check for changes
                var afterText = document.body.innerText;
                var textChanged = afterText.length !== initialText.length;
                
                // Look for any tooltips or new elements
                var tooltips = document.querySelectorAll('[class*="tooltip"], [role="tooltip"], [style*="position: absolute"]');
                var visibleTooltips = [];
                
                for (var j = 0; j < tooltips.length; j++) {{
                    var tooltip = tooltips[j];
                    var style = window.getComputedStyle(tooltip);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && tooltip.textContent.trim()) {{
                        visibleTooltips.push({{
                            text: tooltip.textContent.trim(),
                            class: tooltip.className,
                            visible: true
                        }});
                    }}
                }}
                
                return {{
                    success: true,
                    element_tag: element.tagName,
                    element_class: element.className,
                    text_changed: textChanged,
                    text_length_before: initialText.length,
                    text_length_after: afterText.length,
                    tooltips_found: visibleTooltips.length,
                    tooltips: visibleTooltips,
                    sample_new_text: afterText.length > initialText.length ? afterText.substr(initialText.length, 200) : ''
                }};
            """)
            
            driver.switch_to.default_content()
            
            if click_result['success']:
                print(f"     ✅ Clicked {click_result['element_tag']}.{click_result['element_class']}")
                print(f"     Text changed: {click_result['text_changed']}")
                print(f"     Tooltips found: {click_result['tooltips_found']}")
                
                if click_result['tooltips']:
                    for tooltip in click_result['tooltips']:
                        print(f"     📝 Tooltip: {tooltip['text'][:100]}...")
                
                if click_result['sample_new_text']:
                    print(f"     📄 New text: {click_result['sample_new_text'][:100]}...")
                
                results.append({
                    'marker': marker,
                    'click_result': click_result
                })
            else:
                print(f"     ❌ Click failed: {click_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"     ❌ Error testing marker {i+1}: {e}")
            driver.switch_to.default_content()
    
    return results

def main():
    print("🎯 Simple marker interaction test")
    print("🔧 Fixed iframe access + basic JavaScript clicks")
    
    driver = setup_driver()
    
    try:
        # Load page
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
        print(f"📡 Loading: {url}")
        driver.get(url)
        
        # Wait for loading
        print("⏳ Waiting 30 seconds...")
        time.sleep(30)
        
        # Check main page content first
        main_content = driver.execute_script("return document.body.innerText.length;")
        print(f"📄 Main page text length: {main_content} characters")
        
        # Check iframe properly
        iframe_content, markers = check_iframe_properly(driver)
        
        if iframe_content and markers:
            # Test interactions with markers
            interaction_results = test_simple_marker_clicks(driver, markers)
            
            # Save results
            all_results = {
                'iframe_content': iframe_content,
                'markers_found': markers,
                'interaction_results': interaction_results
            }
            
            with open("simple_marker_results.json", "w") as f:
                json.dump(all_results, f, indent=2, default=str)
            
            print(f"\n💾 Saved results: simple_marker_results.json")
            
            # Summary
            successful_interactions = len([r for r in interaction_results if r['click_result']['success']])
            tooltips_found = sum(r['click_result']['tooltips_found'] for r in interaction_results)
            text_changes = len([r for r in interaction_results if r['click_result']['text_changed']])
            
            print(f"\n📈 Results Summary:")
            print(f"   Markers found in iframe: {len(markers)}")
            print(f"   Successful interactions: {successful_interactions}")
            print(f"   Tooltips revealed: {tooltips_found}")
            print(f"   Text changes detected: {text_changes}")
            
            if tooltips_found > 0:
                print("   ✅ SUCCESS: Found tooltip content!")
                print("   🎯 We can extract project data from tooltips!")
            elif text_changes > 0:
                print("   🟡 PARTIAL: Text changes detected, might need different approach")
            else:
                print("   ❌ No interactive content found with simple clicks")
                
        else:
            print("   ❌ No iframe content or markers found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    main()