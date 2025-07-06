#!/usr/bin/env python3
"""
JavaScript-based IETF Map Extractor - Uses DOM manipulation to find project markers
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

def find_map_markers_via_js(driver):
    """Use JavaScript to find all clickable map markers"""
    
    # JavaScript to find all potential map markers/elements
    marker_finder_script = """
    // Function to find all potential map markers
    function findMapMarkers() {
        var markers = [];
        
        // Look for common Tableau/map marker patterns
        var selectors = [
            'circle',  // SVG circles often used for map markers
            '[class*="mark"]',  // Elements with "mark" in class name
            '[class*="marker"]',  // Elements with "marker" in class name
            '[class*="point"]',   // Elements with "point" in class name
            '[data-mark-type]',   // Tableau data marks
            'g[class*="mark"]',   // SVG groups with mark classes
            'path[class*="mark"]', // SVG paths for markers
            '[role="img"]',       // Images that might be markers
            '.tab-widget-marks path',  // Tableau widget marks
            '.tab-marks circle',       // Tableau marks as circles
            'g.mark circle',          // Groups containing circle markers
            'g[class*="sheet"] circle', // Circles in Tableau sheets
            'g[class*="worksheet"] circle' // Circles in worksheets
        ];
        
        // Search for elements using each selector
        selectors.forEach(function(selector) {
            try {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(element, index) {
                    var rect = element.getBoundingClientRect();
                    
                    // Only include visible elements within reasonable size
                    if (rect.width > 0 && rect.height > 0 && 
                        rect.width < 100 && rect.height < 100 &&
                        rect.top > 0 && rect.left > 0 &&
                        rect.top < window.innerHeight && rect.left < window.innerWidth) {
                        
                        markers.push({
                            element: element,
                            selector: selector,
                            index: index,
                            x: Math.round(rect.left + rect.width/2),
                            y: Math.round(rect.top + rect.height/2),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            tagName: element.tagName,
                            className: element.className || '',
                            id: element.id || '',
                            attributes: Array.from(element.attributes).map(attr => attr.name + '=' + attr.value).join(';')
                        });
                    }
                });
            } catch(e) {
                console.log('Error with selector ' + selector + ':', e);
            }
        });
        
        return markers;
    }
    
    return findMapMarkers();
    """
    
    print("🔍 Searching for map markers using JavaScript...")
    markers = driver.execute_script(marker_finder_script)
    print(f"📍 Found {len(markers)} potential map markers")
    
    return markers

def extract_marker_data(driver, marker_info):
    """Extract data from a specific marker by interacting with it"""
    
    # JavaScript to interact with a specific marker and extract data
    interaction_script = """
    var marker = arguments[0];
    var results = {
        success: false,
        tooltip_text: '',
        page_changes: [],
        error: null
    };
    
    try {
        // Store original page state
        var originalPageText = document.body.innerText;
        
        // Try multiple interaction methods
        var element = document.elementFromPoint(marker.x, marker.y);
        if (!element) {
            results.error = 'No element found at coordinates';
            return results;
        }
        
        // Method 1: Direct click
        element.click();
        
        // Wait a bit for any changes
        setTimeout(function() {
            // Method 2: Mouse events
            var events = ['mouseenter', 'mouseover', 'mousedown', 'mouseup'];
            events.forEach(function(eventType) {
                var event = new MouseEvent(eventType, {
                    bubbles: true,
                    cancelable: true,
                    clientX: marker.x,
                    clientY: marker.y
                });
                element.dispatchEvent(event);
            });
        }, 100);
        
        // Method 3: Focus if it's focusable
        if (element.focus) {
            element.focus();
        }
        
        results.success = true;
        
    } catch(e) {
        results.error = e.toString();
    }
    
    return results;
    """
    
    # Execute the interaction
    result = driver.execute_script(interaction_script, marker_info)
    
    # Wait for potential tooltip/popup to appear
    time.sleep(2)
    
    # Look for any new content that appeared
    tooltip_data = driver.execute_script("""
        var tooltips = [];
        
        // Look for tooltip elements
        var selectors = [
            '[class*="tooltip"]',
            '[role="tooltip"]',
            '[class*="popup"]',
            '[class*="info"]',
            '.viz-tooltip',
            '.tab-tooltip',
            '.tooltip-content'
        ];
        
        selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) {
                if (el.offsetParent !== null && el.textContent.trim()) {
                    tooltips.push({
                        selector: selector,
                        text: el.textContent.trim(),
                        html: el.innerHTML,
                        visible: true
                    });
                }
            });
        });
        
        // Also check for any newly visible text on the page
        var allText = document.body.innerText;
        
        return {
            tooltips: tooltips,
            page_text: allText
        };
    """)
    
    return {
        'marker_info': marker_info,
        'interaction_result': result,
        'tooltip_data': tooltip_data,
        'timestamp': time.time()
    }

def extract_project_details(text_data):
    """Extract structured project details from extracted text"""
    project_details = {}
    
    # Combine all available text
    all_text = ""
    if isinstance(text_data, dict):
        if 'tooltips' in text_data:
            for tooltip in text_data['tooltips']:
                all_text += tooltip.get('text', '') + " "
        if 'page_text' in text_data:
            all_text += text_data['page_text']
    else:
        all_text = str(text_data)
    
    # Extract company name patterns
    company_patterns = [
        r'Company:\s*([A-Za-z0-9\s&\-\.]+?)(?:\n|$|[A-Z][a-z]+:)',
        r'([A-Z][a-zA-Z\s&\-\.]+(?:Ltd|Limited|Company|Corp|Inc|plc|PLC|Group))',
        r'Project lead:\s*([A-Za-z0-9\s&\-\.]+?)(?:\n|$)',
        r'Lead organisation:\s*([A-Za-z0-9\s&\-\.]+?)(?:\n|$)'
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE | re.MULTILINE)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and len(company) < 100:
                project_details['company'] = company
                break
    
    # Extract financial information
    financial_patterns = [
        (r'Total cost:\s*£([\d,]+)', 'total_cost'),
        (r'Total grant:\s*£([\d,]+)', 'total_grant'),
        (r'Grant amount:\s*£([\d,]+)', 'grant_amount'),
        (r'Project cost:\s*£([\d,]+)', 'project_cost'),
        (r'IETF grant:\s*£([\d,]+)', 'ietf_grant'),
        (r'Funding:\s*£([\d,]+)', 'funding')
    ]
    
    for pattern, field_name in financial_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            project_details[field_name] = match.group(1)
    
    # Extract other key fields
    field_patterns = [
        (r'Region:\s*([A-Za-z\s]+?)(?:\n|$|[A-Z][a-z]+:)', 'region'),
        (r'Industry:\s*([A-Za-z\s]+?)(?:\n|$|[A-Z][a-z]+:)', 'industry'),
        (r'Technology:\s*([A-Za-z0-9\s\-\,\.]+?)(?:\n|$|[A-Z][a-z]+:)', 'technology'),
        (r'Project title:\s*([A-Za-z0-9\s\-\,\.]+?)(?:\n|$|[A-Z][a-z]+:)', 'project_title'),
        (r'Solution:\s*([A-Za-z0-9\s\-\,\.]+?)(?:\n|$|[A-Z][a-z]+:)', 'solution'),
        (r'Competition:\s*([A-Za-z0-9\s\-\,\.]+?)(?:\n|$|[A-Z][a-z]+:)', 'competition'),
        (r'Phase:\s*([A-Za-z0-9\s]+?)(?:\n|$|[A-Z][a-z]+:)', 'phase'),
        (r'Status:\s*([A-Za-z0-9\s]+?)(?:\n|$|[A-Z][a-z]+:)', 'status')
    ]
    
    for pattern, field_name in field_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if len(value) > 1 and len(value) < 200:
                project_details[field_name] = value
    
    # Extract all financial amounts for reference
    money_amounts = re.findall(r'£([\d,]+)', all_text)
    if money_amounts:
        project_details['all_financial_amounts'] = money_amounts
    
    return project_details

def main():
    print("🚀 Starting JavaScript-based IETF map extractor...")
    print("🎯 Focus: Direct DOM interaction with map markers")
    
    driver = setup_driver()
    
    try:
        # Load the Tableau page
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
        print(f"📡 Loading: {url}")
        driver.get(url)
        
        # Wait for page to load completely
        print("⏳ Waiting for Tableau to load (30 seconds)...")
        time.sleep(30)
        
        # Take screenshot for reference
        driver.save_screenshot("ietf_js_capture.png")
        print("📸 Saved screenshot: ietf_js_capture.png")
        
        # Find all potential map markers
        markers = find_map_markers_via_js(driver)
        
        if not markers:
            print("❌ No markers found. Let me try a broader search...")
            
            # Fallback: try to find any clickable elements in the map area
            markers = driver.execute_script("""
                var allElements = document.querySelectorAll('*');
                var clickableElements = [];
                
                for (var i = 0; i < allElements.length; i++) {
                    var el = allElements[i];
                    var rect = el.getBoundingClientRect();
                    
                    // Look for small, clickable elements that could be markers
                    if (rect.width > 5 && rect.width < 50 && 
                        rect.height > 5 && rect.height < 50 &&
                        rect.left > 100 && rect.left < 800 &&
                        rect.top > 100 && rect.top < 700) {
                        
                        clickableElements.push({
                            x: Math.round(rect.left + rect.width/2),
                            y: Math.round(rect.top + rect.height/2),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            tagName: el.tagName,
                            className: el.className || '',
                            id: el.id || ''
                        });
                    }
                }
                
                return clickableElements;
            """)
            
            print(f"🔄 Fallback search found {len(markers)} potential elements")
        
        if markers:
            extracted_projects = []
            
            print(f"🔍 Extracting data from {len(markers)} markers...")
            
            for i, marker in enumerate(markers):
                if i % 10 == 0:
                    print(f"   Progress: {i}/{len(markers)} markers processed...")
                
                try:
                    # Extract data from this marker
                    marker_data = extract_marker_data(driver, marker)
                    
                    # Parse the extracted text for project details
                    project_details = extract_project_details(marker_data['tooltip_data'])
                    
                    # Only keep markers that have meaningful project data
                    if project_details and (project_details.get('company') or 
                                          project_details.get('total_cost') or 
                                          project_details.get('project_title')):
                        
                        project_entry = {
                            'marker_index': i,
                            'marker_coordinates': {'x': marker['x'], 'y': marker['y']},
                            'marker_details': marker,
                            'project_details': project_details,
                            'raw_data': marker_data,
                            'timestamp': time.time()
                        }
                        
                        extracted_projects.append(project_entry)
                        
                        company = project_details.get('company', 'Unknown')
                        cost = project_details.get('total_cost', 'Unknown')
                        print(f"   ✅ Project found: {company} - £{cost}")
                        
                        # Small delay between markers
                        time.sleep(0.5)
                
                except Exception as e:
                    print(f"   ❌ Error with marker {i}: {e}")
                    continue
            
            print(f"\n🎉 Extraction completed!")
            print(f"📊 Found {len(extracted_projects)} projects with meaningful data")
            
            if extracted_projects:
                # Save detailed results
                with open("ietf_js_projects.json", "w") as f:
                    json.dump(extracted_projects, f, indent=2, default=str)
                print(f"💾 Saved detailed project data: ietf_js_projects.json")
                
                # Create comprehensive CSV
                csv_data = []
                for project in extracted_projects:
                    details = project['project_details']
                    marker = project['marker_details']
                    
                    row = {
                        'marker_index': project['marker_index'],
                        'x_coordinate': marker['x'],
                        'y_coordinate': marker['y'],
                        'marker_type': marker.get('tagName', ''),
                        'marker_class': marker.get('className', ''),
                        'company': details.get('company', ''),
                        'project_title': details.get('project_title', ''),
                        'region': details.get('region', ''),
                        'industry': details.get('industry', ''),
                        'technology': details.get('technology', ''),
                        'solution': details.get('solution', ''),
                        'total_cost': details.get('total_cost', ''),
                        'total_grant': details.get('total_grant', ''),
                        'grant_amount': details.get('grant_amount', ''),
                        'ietf_grant': details.get('ietf_grant', ''),
                        'competition': details.get('competition', ''),
                        'phase': details.get('phase', ''),
                        'status': details.get('status', ''),
                        'financial_amounts': ', '.join(details.get('all_financial_amounts', [])),
                        'has_company': bool(details.get('company')),
                        'has_financial_data': bool(details.get('total_cost') or details.get('total_grant')),
                        'data_richness_score': len([v for v in details.values() if v])
                    }
                    csv_data.append(row)
                
                df = pd.DataFrame(csv_data)
                df.to_csv("ietf_js_projects.csv", index=False)
                print(f"📊 Saved CSV with {len(csv_data)} projects: ietf_js_projects.csv")
                
                # Print detailed summary
                companies = [p['project_details'].get('company') for p in extracted_projects if p['project_details'].get('company')]
                regions = [p['project_details'].get('region') for p in extracted_projects if p['project_details'].get('region')]
                costs = [p['project_details'].get('total_cost') for p in extracted_projects if p['project_details'].get('total_cost')]
                
                print("\n📈 Extraction Summary:")
                print(f"   Total markers found: {len(markers)}")
                print(f"   Projects with data: {len(extracted_projects)}")
                print(f"   Companies identified: {len(companies)}")
                print(f"   Regions found: {len(set(regions))}")
                print(f"   Projects with costs: {len(costs)}")
                
                if companies:
                    print(f"   Sample companies: {', '.join(companies[:3])}")
                if regions:
                    print(f"   Sample regions: {', '.join(set(regions)[:5])}")
                if costs:
                    print(f"   Sample costs: £{', £'.join(costs[:3])}")
                    
            else:
                print("❌ No projects with meaningful data found.")
                print("   The markers might not contain the expected tooltip content.")
                
        else:
            print("❌ No markers found at all. The map might use a different structure.")
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    main()