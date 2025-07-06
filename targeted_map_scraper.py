#!/usr/bin/env python3
"""
Targeted IETF Map Scraper - Grid-based approach to find actual project markers
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
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

def clear_all_tooltips(driver):
    """Clear any existing tooltips/overlays"""
    driver.execute_script("""
        // Remove any existing tooltips
        document.querySelectorAll('[class*="tooltip"], [role="tooltip"]').forEach(el => el.remove());
        
        // Clear any overlay elements
        document.querySelectorAll('[class*="overlay"], [class*="popup"]').forEach(el => {
            if (el.style) el.style.display = 'none';
        });
    """)

def get_map_grid_coordinates():
    """Define grid coordinates focused on the actual map area"""
    # Based on typical Tableau layout, the map should be in the center-left area
    # Avoiding the right side (filters) and bottom (legends)
    
    map_area = {
        'left': 150,    # Start after left margin
        'right': 700,   # Stop before right-side filters  
        'top': 150,     # Start after top navigation
        'bottom': 650   # Stop before bottom legend
    }
    
    # Create a grid of points to test
    grid_points = []
    step_x = 50  # Test every 50 pixels horizontally
    step_y = 40  # Test every 40 pixels vertically
    
    for x in range(map_area['left'], map_area['right'], step_x):
        for y in range(map_area['top'], map_area['bottom'], step_y):
            grid_points.append((x, y))
    
    print(f"📍 Created grid with {len(grid_points)} test points in map area")
    return grid_points

def test_coordinate_for_tooltip(driver, x, y, coord_index):
    """Test a specific coordinate for tooltip content"""
    try:
        # Clear any existing tooltips first
        clear_all_tooltips(driver)
        time.sleep(0.3)
        
        # Move to coordinate and hover
        actions = ActionChains(driver)
        actions.move_by_offset(x - 960, y - 540).perform()  # Move relative to center
        time.sleep(1)
        
        # Also try clicking at the coordinate
        driver.execute_script(f"""
            var element = document.elementFromPoint({x}, {y});
            if (element) {{
                // Dispatch mouseover event
                var mouseEvent = new MouseEvent('mouseover', {{
                    bubbles: true,
                    cancelable: true,
                    clientX: {x},
                    clientY: {y}
                }});
                element.dispatchEvent(mouseEvent);
                
                // Also try click after a delay
                setTimeout(function() {{
                    element.click();
                }}, 200);
            }}
        """)
        
        time.sleep(2)  # Wait for tooltip to appear
        
        # Look for tooltip content
        tooltip_data = {}
        
        # Check for various tooltip types
        tooltip_selectors = [
            "[class*='tooltip']:not([style*='display: none'])",
            "[role='tooltip']:not([style*='display: none'])",
            "[class*='viz-tooltip']:not([style*='display: none'])",
            "[class*='tab-tooltip']:not([style*='display: none'])"
        ]
        
        found_tooltip = False
        for selector in tooltip_selectors:
            try:
                tooltips = driver.find_elements(By.CSS_SELECTOR, selector)
                for tooltip in tooltips:
                    if tooltip.is_displayed():
                        text = tooltip.text.strip()
                        if text and len(text) > 20:  # Meaningful content
                            # Check if it's NOT a filter tooltip
                            if not any(term in text.lower() for term in ['filter', 'showing all values', 'search', 'context menu']):
                                tooltip_data[selector] = text
                                found_tooltip = True
                                print(f"   🎯 Found tooltip at ({x},{y}): {text[:100]}...")
                                break
            except:
                continue
        
        # Also check for any project-specific text that appears
        if found_tooltip:
            project_text = driver.execute_script("""
                var texts = [];
                var elements = document.querySelectorAll('*');
                
                for (var i = 0; i < elements.length; i++) {
                    var el = elements[i];
                    if (el.offsetParent !== null && el.textContent) {
                        var text = el.textContent.trim();
                        // Look for project-specific patterns
                        if (text.length > 10 && text.length < 2000 && 
                            (text.match(/£[\\d,]+/) || 
                             text.includes('Total cost') ||
                             text.includes('Total grant') ||
                             text.includes('Company') ||
                             text.includes('Project') ||
                             text.includes('Technology') ||
                             text.includes('Region') ||
                             text.includes('Industry') ||
                             text.match(/Ltd|Limited|plc|PLC|Corp|Inc/))) {
                            texts.push(text);
                        }
                    }
                }
                
                // Remove duplicates and return unique texts
                return [...new Set(texts)].slice(0, 10);
            """)
            
            if project_text:
                tooltip_data['project_text'] = project_text
        
        # Reset mouse position
        actions.move_by_offset(-(x - 960), -(y - 540)).perform()
        
        return tooltip_data if tooltip_data else None
        
    except Exception as e:
        print(f"   ❌ Error testing coordinate ({x},{y}): {e}")
        return None

def extract_project_details(tooltip_text):
    """Extract structured project details from tooltip text"""
    project_details = {}
    
    # Combine all text if it's a list
    if isinstance(tooltip_text, list):
        all_text = " ".join(tooltip_text)
    else:
        all_text = str(tooltip_text)
    
    # Extract company name
    company_patterns = [
        r'([A-Z][a-zA-Z\s&\-]+(?:Ltd|Limited|Company|Corp|Inc|plc|PLC))',
        r'([A-Z][a-zA-Z\s&\-]{5,50}(?=\s+(?:Industry|Project|Technology|Region)))'
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            if len(company) > 3:
                project_details['company'] = company
                break
    
    # Extract financial information
    cost_match = re.search(r'Total cost:\s*£([\d,]+)', all_text)
    if cost_match:
        project_details['total_cost'] = cost_match.group(1)
    
    grant_match = re.search(r'Total grant:\s*£([\d,]+)', all_text)
    if grant_match:
        project_details['total_grant'] = grant_match.group(1)
    
    # Extract other financial amounts
    money_amounts = re.findall(r'£([\d,]+)', all_text)
    if money_amounts:
        project_details['financial_amounts'] = money_amounts
    
    # Extract region
    region_match = re.search(r'Region:\s*([A-Za-z\s]+)', all_text)
    if region_match:
        project_details['region'] = region_match.group(1).strip()
    
    # Extract industry
    industry_match = re.search(r'Industry:\s*([A-Za-z\s]+)', all_text)
    if industry_match:
        project_details['industry'] = industry_match.group(1).strip()
    
    # Extract technology/solution
    tech_patterns = [
        r'Technology:\s*([^\\n]+)',
        r'Solution:\s*([^\\n]+)'
    ]
    
    for pattern in tech_patterns:
        match = re.search(pattern, all_text)
        if match:
            project_details['technology'] = match.group(1).strip()
            break
    
    # Extract project type
    if 'Feasibility Study' in all_text:
        project_details['project_type'] = 'Feasibility Study'
    elif 'Demonstration' in all_text:
        project_details['project_type'] = 'Demonstration'
    elif re.search(r'Phase\s+(\d+)', all_text):
        phase_match = re.search(r'Phase\s+(\d+)', all_text)
        project_details['project_type'] = f"Phase {phase_match.group(1)}"
    
    # Extract competition/year
    comp_match = re.search(r'Competition:\s*([^\\n]+)', all_text)
    if comp_match:
        project_details['competition'] = comp_match.group(1).strip()
    
    return project_details

def main():
    print("🚀 Starting targeted IETF map scraper...")
    print("🎯 Focus: Grid-based coordinate testing for actual project markers")
    
    driver = setup_driver()
    
    try:
        # Load the Tableau page
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no"
        print(f"📡 Loading: {url}")
        driver.get(url)
        
        # Wait for page to load completely
        print("⏳ Waiting for Tableau to load (45 seconds)...")
        time.sleep(45)
        
        # Take screenshot for reference
        driver.save_screenshot("ietf_targeted_capture.png")
        print("📸 Saved screenshot: ietf_targeted_capture.png")
        
        # Get grid coordinates to test
        grid_points = get_map_grid_coordinates()
        
        # Test each coordinate for tooltip content
        found_projects = []
        
        print(f"🔍 Testing {len(grid_points)} coordinates for project data...")
        
        for i, (x, y) in enumerate(grid_points):
            if i % 20 == 0:  # Progress update every 20 points
                print(f"   Progress: {i}/{len(grid_points)} coordinates tested...")
            
            tooltip_data = test_coordinate_for_tooltip(driver, x, y, i)
            
            if tooltip_data:
                # Extract project details
                all_tooltip_text = ""
                for key, value in tooltip_data.items():
                    if isinstance(value, str):
                        all_tooltip_text += value + " "
                    elif isinstance(value, list):
                        all_tooltip_text += " ".join(value) + " "
                
                project_details = extract_project_details(all_tooltip_text)
                
                project_entry = {
                    'coordinate_index': i,
                    'x_coordinate': x,
                    'y_coordinate': y,
                    'raw_tooltip_data': tooltip_data,
                    'project_details': project_details,
                    'full_text': all_tooltip_text,
                    'timestamp': time.time()
                }
                
                found_projects.append(project_entry)
                
                company = project_details.get('company', 'Unknown Company')
                region = project_details.get('region', 'Unknown Region')
                print(f"   ✅ Project found at ({x},{y}): {company} - {region}")
                
                # Small delay after finding a project
                time.sleep(1)
        
        print(f"\n🎉 Completed coordinate testing!")
        print(f"📊 Found {len(found_projects)} projects with data")
        
        if found_projects:
            # Save detailed results
            with open("ietf_targeted_projects.json", "w") as f:
                json.dump(found_projects, f, indent=2, default=str)
            print(f"💾 Saved detailed project data: ietf_targeted_projects.json")
            
            # Create comprehensive CSV
            csv_data = []
            for project in found_projects:
                details = project['project_details']
                row = {
                    'coordinate_index': project['coordinate_index'],
                    'x_coordinate': project['x_coordinate'],
                    'y_coordinate': project['y_coordinate'],
                    'company': details.get('company', ''),
                    'region': details.get('region', ''),
                    'industry': details.get('industry', ''),
                    'technology': details.get('technology', ''),
                    'project_type': details.get('project_type', ''),
                    'total_cost': details.get('total_cost', ''),
                    'total_grant': details.get('total_grant', ''),
                    'competition': details.get('competition', ''),
                    'financial_amounts': ', '.join(details.get('financial_amounts', [])),
                    'full_text_length': len(project['full_text']),
                    'has_company': bool(details.get('company')),
                    'has_financial_data': bool(details.get('total_cost') or details.get('total_grant'))
                }
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            df.to_csv("ietf_targeted_projects.csv", index=False)
            print(f"📊 Saved CSV with {len(csv_data)} projects: ietf_targeted_projects.csv")
            
            # Print detailed summary
            companies = [p['project_details'].get('company') for p in found_projects if p['project_details'].get('company')]
            regions = [p['project_details'].get('region') for p in found_projects if p['project_details'].get('region')]
            costs = [p['project_details'].get('total_cost') for p in found_projects if p['project_details'].get('total_cost')]
            
            print("\n📈 Detailed Extraction Summary:")
            print(f"   Total coordinates tested: {len(grid_points)}")
            print(f"   Projects found: {len(found_projects)}")
            print(f"   Companies identified: {len(companies)}")
            print(f"   Regions identified: {len(regions)}")
            print(f"   Projects with costs: {len(costs)}")
            
            if companies:
                print(f"   Sample companies: {', '.join(companies[:3])}")
            if regions:
                print(f"   Sample regions: {', '.join(set(regions)[:3])}")
            
        else:
            print("❌ No projects found. The map markers might be in a different area or use different interaction methods.")
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    main()