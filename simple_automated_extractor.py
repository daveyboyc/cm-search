#!/usr/bin/env python3
"""
Simple Automated IETF Extractor - Compatible Chrome options
"""
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

class SimpleIETFExtractor:
    def __init__(self):
        self.driver = None
        self.all_projects = []
        
    def setup_driver(self):
        """Setup Chrome driver with simple options"""
        print("🚀 Setting up Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✅ Chrome driver ready")
        
    def load_tableau_page(self):
        """Load the IETF Tableau page and wait for it to be ready"""
        print("📄 Loading IETF Tableau page...")
        
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard"
        self.driver.get(url)
        
        # Wait for page to load
        print("⏳ Waiting for page to load...")
        time.sleep(15)
        
        # Wait for iframe to appear
        try:
            print("🔍 Looking for iframe...")
            iframe = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            print("✅ Iframe found, switching context...")
            self.driver.switch_to.frame(iframe)
            
            # Wait for map content to load
            time.sleep(10)
            print("✅ Map content loaded")
            
        except Exception as e:
            print(f"❌ Error loading iframe: {e}")
            print("🔍 Checking page structure...")
            
            # Print page info for debugging
            print(f"Current URL: {self.driver.current_url}")
            print(f"Page title: {self.driver.title}")
            
            # Try to find any content
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*")
            print(f"Total elements found: {len(all_elements)}")
            
            return False
            
        return True
    
    def find_all_markers(self):
        """Find all clickable markers on the map"""
        print("🎯 Finding all map markers...")
        
        # Wait a bit more for map to fully render
        time.sleep(5)
        
        # Try different approaches to find markers
        marker_strategies = [
            # SVG circles (most likely for Tableau maps)
            ("CSS", "circle"),
            ("CSS", "svg circle"),
            ("CSS", ".mark circle"),
            ("CSS", "[data-tb-test-id*='mark'] circle"),
            
            # General clickable elements in visualization
            ("CSS", "[class*='mark']"),
            ("CSS", "[data-tb-test-id*='mark']"),
            ("CSS", ".tab-widget circle"),
            
            # Backup: any small clickable elements
            ("XPATH", "//circle[@r]"),
            ("XPATH", "//*[contains(@class, 'mark')]"),
        ]
        
        all_markers = []
        
        for strategy_type, selector in marker_strategies:
            try:
                if strategy_type == "CSS":
                    markers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                else:  # XPATH
                    markers = self.driver.find_elements(By.XPATH, selector)
                
                # Filter for visible, enabled markers
                valid_markers = []
                for marker in markers:
                    try:
                        if (marker.is_displayed() and 
                            marker.is_enabled() and 
                            marker.size['width'] > 2 and 
                            marker.size['height'] > 2):
                            valid_markers.append(marker)
                    except:
                        continue
                
                if valid_markers:
                    print(f"✅ Found {len(valid_markers)} markers with {strategy_type}: {selector}")
                    all_markers = valid_markers
                    break
                    
            except Exception as e:
                print(f"⚠️ Strategy {strategy_type}:{selector} failed: {e}")
                continue
        
        if not all_markers:
            print("❌ No markers found with standard selectors")
            print("🔍 Trying to find ANY clickable elements...")
            
            # Last resort: find any clickable elements
            try:
                all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*")
                clickable_elements = []
                
                for element in all_elements:
                    try:
                        if (element.is_displayed() and 
                            element.is_enabled() and 
                            element.size['width'] > 5 and 
                            element.size['height'] > 5 and
                            element.size['width'] < 50 and  # Likely a marker, not a big element
                            element.size['height'] < 50):
                            
                            # Check if it might be a marker
                            tag_name = element.tag_name.lower()
                            class_name = element.get_attribute('class') or ''
                            
                            if (tag_name in ['circle', 'path', 'rect'] or 
                                'mark' in class_name.lower() or
                                'point' in class_name.lower()):
                                clickable_elements.append(element)
                                
                    except:
                        continue
                
                if clickable_elements:
                    print(f"🔍 Found {len(clickable_elements)} potential marker elements")
                    all_markers = clickable_elements[:20]  # Limit to first 20
            
            except Exception as e:
                print(f"❌ Last resort search failed: {e}")
                return []
        
        # Remove duplicates by location
        unique_markers = []
        seen_locations = set()
        
        for marker in all_markers:
            try:
                location = marker.location
                location_key = f"{round(location['x'])},{round(location['y'])}"
                if location_key not in seen_locations:
                    seen_locations.add(location_key)
                    unique_markers.append(marker)
            except:
                continue
        
        print(f"🎯 Final count: {len(unique_markers)} unique markers")
        return unique_markers
    
    def click_marker_and_wait(self, marker, marker_index):
        """Click a marker and wait for tooltip to appear"""
        print(f"\n🎯 Clicking marker {marker_index + 1}...")
        
        try:
            # Scroll to marker
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", marker)
            time.sleep(1)
            
            # Get marker info for debugging
            location = marker.location
            size = marker.size
            print(f"📍 Marker location: ({location['x']}, {location['y']}) size: {size['width']}x{size['height']}")
            
            # Click the marker
            ActionChains(self.driver).move_to_element(marker).click().perform()
            print(f"✅ Clicked marker {marker_index + 1}")
            
            # Wait for tooltip/popup to appear
            time.sleep(4)
            
            # Try to extract data from the page
            project_data = self.extract_data_from_page()
            
            if project_data:
                project_data['marker_index'] = marker_index + 1
                project_data['marker_location'] = location
                return project_data
            else:
                print(f"⚠️ No data found for marker {marker_index + 1}")
                return None
            
        except Exception as e:
            print(f"❌ Error with marker {marker_index + 1}: {e}")
            return None
    
    def extract_data_from_page(self):
        """Extract project data from the current page state"""
        print("📄 Extracting data from page...")
        
        project_data = {}
        
        # Strategy 1: Look for tooltip/popup containers
        tooltip_selectors = [
            "[class*='tooltip']",
            "[class*='popup']",
            "[class*='info']",
            ".tab-tooltip",
            "[data-tb-test-id*='tooltip']",
            "[role='tooltip']",
            ".qtip",
            "[id*='tooltip']"
        ]
        
        for selector in tooltip_selectors:
            try:
                tooltips = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for tooltip in tooltips:
                    if tooltip.is_displayed():
                        text = tooltip.text.strip()
                        if len(text) > 50:  # Substantial content
                            print(f"✅ Found tooltip with {len(text)} characters")
                            parsed_data = self.parse_tooltip_text(text)
                            if parsed_data:
                                return parsed_data
            except:
                continue
        
        # Strategy 2: Look for any text that appears to be project info
        print("🔍 Searching for project text in page...")
        
        # Get all text content from the page
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for patterns that indicate project data
            if any(keyword in page_text.lower() for keyword in ['industry:', 'competition:', 'region:', 'total cost:', 'total grant:']):
                print("✅ Found project-like text in page")
                parsed_data = self.parse_tooltip_text(page_text)
                if parsed_data:
                    return parsed_data
        except:
            pass
        
        # Strategy 3: Check for any new text that appeared after clicking
        print("🔍 Looking for dynamic content...")
        
        # Take a screenshot for debugging
        try:
            screenshot_path = f"marker_click_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"📸 Screenshot saved: {screenshot_path}")
        except:
            pass
        
        return None
    
    def parse_tooltip_text(self, text):
        """Parse tooltip text into structured data"""
        if not text or len(text) < 20:
            return None
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        project_data = {}
        
        # Look for company name (line with Ltd, Limited, etc.)
        for line in lines:
            if (not project_data.get('company_name') and 
                re.search(r'(Ltd|Limited|PLC|Group|Company|Industries)', line, re.IGNORECASE) and
                len(line) < 100):  # Not too long to be description
                project_data['company_name'] = line
                break
        
        # Parse structured fields
        for line in lines:
            line_lower = line.lower()
            
            if line.startswith('Industry:') or 'industry:' in line_lower:
                project_data['industry'] = re.sub(r'^industry:\s*', '', line, flags=re.IGNORECASE).strip()
            elif line.startswith('Competition:') or 'competition:' in line_lower:
                project_data['competition'] = re.sub(r'^competition:\s*', '', line, flags=re.IGNORECASE).strip()
            elif line.startswith('Region:') or 'region:' in line_lower:
                project_data['region'] = re.sub(r'^region:\s*', '', line, flags=re.IGNORECASE).strip()
            elif line.startswith('Project type:') or 'project type:' in line_lower:
                project_data['project_type'] = re.sub(r'^project type:\s*', '', line, flags=re.IGNORECASE).strip()
            elif line.startswith('Technology:') or 'technology:' in line_lower:
                project_data['technology'] = re.sub(r'^technology:\s*', '', line, flags=re.IGNORECASE).strip()
            elif line.startswith('Solution:') or 'solution:' in line_lower:
                project_data['solution'] = re.sub(r'^solution:\s*', '', line, flags=re.IGNORECASE).strip()
            elif 'total cost:' in line_lower:
                cost_match = re.search(r'£?([0-9,]+)', line)
                if cost_match:
                    project_data['total_cost'] = cost_match.group(1)
            elif 'total grant:' in line_lower:
                grant_match = re.search(r'£?([0-9,]+)', line)
                if grant_match:
                    project_data['total_grant'] = grant_match.group(1)
        
        # Look for description (longer text that doesn't match field patterns)
        for line in lines:
            if (len(line) > 80 and 
                not any(field in line.lower() for field in ['industry:', 'competition:', 'region:', 'technology:', 'total cost:', 'total grant:'])):
                if 'description' not in project_data:
                    project_data['description'] = line
                    break
        
        # Only return if we found some meaningful data
        if len(project_data) >= 2:  # At least 2 fields
            return project_data
        
        return None
    
    def run_extraction(self):
        """Run the complete extraction process"""
        print("🤖 Simple Automated IETF Extraction")
        print("=" * 50)
        
        try:
            # Setup
            self.setup_driver()
            
            # Load page
            if not self.load_tableau_page():
                print("❌ Failed to load Tableau page")
                return False
            
            # Find markers
            markers = self.find_all_markers()
            if not markers:
                print("❌ No markers found")
                return False
            
            print(f"\n🎯 Processing {len(markers)} markers...")
            
            # Process each marker
            successful_extractions = 0
            for i, marker in enumerate(markers):
                project_data = self.click_marker_and_wait(marker, i)
                if project_data:
                    self.all_projects.append(project_data)
                    company = project_data.get('company_name', 'Unknown Company')
                    print(f"✅ Success {successful_extractions + 1}: {company}")
                    successful_extractions += 1
                
                # Brief pause between markers
                time.sleep(3)
                
                # Break early if we're not finding anything
                if i >= 5 and successful_extractions == 0:
                    print("⚠️ No successful extractions after 5 attempts, may need to adjust strategy")
                    break
            
            # Save results
            if self.all_projects:
                self.save_results()
                print(f"\n🎉 SUCCESS! Extracted {len(self.all_projects)} projects")
            else:
                print("\n❌ No projects extracted")
            
            return len(self.all_projects) > 0
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            return False
            
        finally:
            if self.driver:
                input("Press Enter to close browser (for debugging)...")
                self.driver.quit()
    
    def save_results(self):
        """Save extraction results"""
        print("💾 Saving results...")
        
        # Save JSON
        with open("automated_ietf_projects.json", "w", encoding="utf-8") as f:
            json.dump(self.all_projects, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary = f"# Automated IETF Extraction Results\n\n"
        summary += f"**Projects Extracted:** {len(self.all_projects)}\n\n"
        
        for i, project in enumerate(self.all_projects, 1):
            summary += f"## Project {i}\n"
            for key, value in project.items():
                if key != 'marker_location':
                    summary += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            summary += "\n"
        
        with open("automated_extraction_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
        
        print("💾 Saved: automated_ietf_projects.json")
        print("💾 Saved: automated_extraction_summary.md")

def main():
    extractor = SimpleIETFExtractor()
    success = extractor.run_extraction()
    
    if success:
        print("✅ Automated extraction completed!")
    else:
        print("❌ Extraction failed - check browser for debugging")

if __name__ == "__main__":
    main() 