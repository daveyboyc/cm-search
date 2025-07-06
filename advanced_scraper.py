#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import json
import time

def main():
    print("🚀 Starting advanced IETF project data extraction...")
    
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("perfLoggingPrefs", {"enableNetwork": True})
    options.add_experimental_option("loggingPrefs", {"performance": "ALL"})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
        print(f"📡 Loading: {url}")
        driver.get(url)
        time.sleep(60)  # Wait for full load
        
        driver.save_screenshot("ietf_loaded.png")
        print("📸 Saved screenshot: ietf_loaded.png")
        
        # Find interactive map elements
        print("🔍 Finding map markers...")
        marker_script = """
        var results = [];
        var selectors = ['circle', 'path[d*="M"]', '[data-tb-test-id*="mark"]', '.mark'];
        
        selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var rect = el.getBoundingClientRect();
                if (rect.width > 1 && rect.height > 1 && rect.width < 500) {
                    results.push({
                        index: results.length,
                        tag: el.tagName,
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2),
                        selector: selector
                    });
                }
            }
        });
        return results.slice(0, 30);
        """
        
        markers = driver.execute_script(marker_script)
        print(f"🎯 Found {len(markers)} potential markers")
        
        # Interact with markers to get data
        print("🔍 Extracting data from markers...")
        project_data = []
        actions = ActionChains(driver)
        
        for i, marker in enumerate(markers[:15]):  # Process first 15
            try:
                print(f"   Processing marker {i+1}/15...")
                
                # Click on marker position
                driver.execute_script(f"document.elementFromPoint({marker['x']}, {marker['y']})?.click();")
                time.sleep(3)
                
                # Look for tooltips and popups
                tooltip_text = ""
                selectors = ['[class*="tooltip"]', '[role="tooltip"]', '[class*="popup"]']
                
                for selector in selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.text.strip():
                            tooltip_text = element.text.strip()
                            break
                    if tooltip_text:
                        break
                
                # Get any visible text that appeared
                new_text = driver.execute_script("""
                    var visible = [];
                    var all = document.querySelectorAll('*');
                    for (var i = 0; i < all.length; i++) {
                        var el = all[i];
                        if (el.offsetParent && el.textContent && 
                            el.textContent.trim().length > 5 && 
                            el.textContent.trim().length < 100) {
                            visible.push(el.textContent.trim());
                        }
                    }
                    return visible.slice(-5);
                """)
                
                if tooltip_text or (new_text and len(new_text) > 0):
                    project_data.append({
                        'marker_index': i,
                        'position': f"{marker['x']},{marker['y']}",
                        'tooltip': tooltip_text,
                        'visible_text': ' | '.join(new_text) if new_text else '',
                        'marker_info': marker
                    })
                    print(f"     ✅ Found data: {tooltip_text[:50]}..." if tooltip_text else f"     ✅ Found text data")
                
            except Exception as e:
                print(f"     ❌ Error: {e}")
        
        # Save results
        results = {
            'timestamp': time.time(),
            'total_markers': len(markers),
            'processed_markers': len(project_data),
            'project_data': project_data,
            'all_markers': markers
        }
        
        with open("ietf_advanced_extraction.json", "w") as f:
            json.dump(results, f, indent=2)
        
        if project_data:
            df = pd.DataFrame(project_data)
            df.to_csv("ietf_extracted_projects.csv", index=False)
            print(f"💾 Saved {len(project_data)} projects to CSV")
        
        driver.save_screenshot("ietf_final_extraction.png")
        
        print(f"\n🏁 Complete! Processed {len(project_data)}/{len(markers)} markers")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        time.sleep(10)
        driver.quit()

if __name__ == "__main__":
    main() 