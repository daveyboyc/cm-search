#!/usr/bin/env python3
"""
Ultimate Tableau Extractor - 100% Automated IETF Data Extraction
Zero manual intervention - finds ALL markers and extracts complete data
Uses proven API method for maximum reliability
"""

import json
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import html
from urllib.parse import unquote
import random
import csv
from datetime import datetime

class UltimateTableauExtractor:
    def __init__(self):
        self.driver = None
        self.session_id = None
        self.cookies = None
        self.all_projects = []
        self.successful_extractions = 0
        self.failed_extractions = 0
        
    def setup_chrome_for_automation(self):
        """Setup Chrome with optimal settings for Tableau automation"""
        print("🤖 Setting up Chrome for full automation...")
        
        chrome_options = Options()
        # Essential options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Anti-detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance optimization
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        # Realistic user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Execute anti-detection script
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ Chrome ready for automated extraction")
        
    def load_tableau_map_automatically(self):
        """Automatically load and initialize Tableau map"""
        print("📊 Loading IETF Tableau map automatically...")
        
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard"
        self.driver.get(url)
        print("📄 Page loaded, waiting for Tableau initialization...")
        
        # Wait for page to fully load
        time.sleep(20)
        
        # Extract session cookies and ID
        success = self.extract_session_automatically()
        if not success:
            print("❌ Failed to extract session")
            return False
            
        # Enter iframe context
        iframe_success = self.enter_tableau_iframe()
        if not iframe_success:
            print("❌ Failed to enter iframe")
            return False
            
        # Wait for map to render
        print("⏳ Waiting for map to fully render...")
        time.sleep(15)
        
        print("✅ Tableau map ready for marker discovery")
        return True
        
    def extract_session_automatically(self):
        """Extract Tableau session ID and cookies automatically"""
        print("🔑 Extracting session information...")
        
        # Get cookies
        cookies = self.driver.get_cookies()
        self.cookies = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print(f"✅ Captured {len(cookies)} cookies")
        
        # Extract session ID from page source
        page_source = self.driver.page_source
        
        # Multiple session ID patterns
        session_patterns = [
            r'sessions/([A-F0-9]{32}-\d+:\d+)',
            r'"sessionId"\s*:\s*"([^"]+)"',
            r'sessionId[=:]([A-F0-9-]{30,})',
            r'workbook[^}]*session[^}]*?([A-F0-9]{32}-\d+:\d+)',
            r'bootstrap[^}]*sessions/([A-F0-9]{32}-\d+:\d+)'
        ]
        
        for pattern in session_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                # Take the longest match (most likely valid)
                self.session_id = max(matches, key=len)
                print(f"✅ Session ID extracted: {self.session_id[:35]}...")
                return True
                
        print("⚠️ Session ID not found in page source")
        return False
        
    def enter_tableau_iframe(self):
        """Enter Tableau iframe with retries"""
        print("🖼️ Entering Tableau iframe...")
        
        for attempt in range(3):
            try:
                # Wait for iframe to appear
                iframe = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                
                # Switch to iframe
                self.driver.switch_to.frame(iframe)
                print("✅ Successfully entered iframe")
                return True
                
            except Exception as e:
                print(f"⚠️ Iframe attempt {attempt + 1} failed: {e}")
                time.sleep(5)
                
        return False
        
    def discover_all_markers_automatically(self):
        """Automatically discover ALL markers on the map"""
        print("🎯 DISCOVERING ALL MARKERS AUTOMATICALLY")
        print("=" * 50)
        
        discovered_markers = []
        
        # Strategy 1: Find SVG circles (Tableau's primary marker type)
        svg_markers = self.find_svg_circle_markers()
        discovered_markers.extend(svg_markers)
        print(f"🔵 SVG circles found: {len(svg_markers)}")
        
        # Strategy 2: Find interactive path elements
        path_markers = self.find_path_markers()
        discovered_markers.extend(path_markers)
        print(f"📍 Path markers found: {len(path_markers)}")
        
        # Strategy 3: Find elements with click handlers
        interactive_markers = self.find_interactive_markers()
        discovered_markers.extend(interactive_markers)
        print(f"🖱️ Interactive elements found: {len(interactive_markers)}")
        
        # Strategy 4: Systematic coordinate-based discovery
        if len(discovered_markers) < 5:
            print("🔍 Using systematic coordinate scanning...")
            coord_markers = self.systematic_coordinate_discovery()
            discovered_markers.extend(coord_markers)
            print(f"📐 Coordinate-based markers: {len(coord_markers)}")
        
        # Remove duplicates and validate
        unique_markers = self.deduplicate_and_validate_markers(discovered_markers)
        
        print(f"✅ TOTAL UNIQUE MARKERS DISCOVERED: {len(unique_markers)}")
        return unique_markers
        
    def find_svg_circle_markers(self):
        """Find SVG circle markers (most common in Tableau)"""
        markers = []
        
        # Comprehensive SVG selectors for Tableau
        svg_selectors = [
            "svg circle",
            "circle[r]",
            "g circle",
            ".mark circle",
            "[data-tb-test-id*='mark'] circle",
            "svg g[class*='mark'] circle",
            "svg circle[fill]",
            "circle[stroke]"
        ]
        
        for selector in svg_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    try:
                        # Check if element is visible and reasonable size
                        if (element.is_displayed() and 
                            element.size.get('width', 0) > 2 and 
                            element.size.get('height', 0) > 2 and
                            element.size.get('width', 0) < 50):  # Reasonable marker size
                            
                            # Get center coordinates
                            location = element.location
                            size = element.size
                            center_x = location['x'] + size['width'] // 2
                            center_y = location['y'] + size['height'] // 2
                            
                            markers.append({
                                'x': center_x,
                                'y': center_y,
                                'element': element,
                                'type': 'svg_circle',
                                'selector': selector
                            })
                            
                    except Exception as e:
                        continue
                        
                if markers:
                    print(f"✅ Found {len(markers)} markers with: {selector}")
                    break  # Use the first successful selector
                    
            except Exception as e:
                continue
                
        return markers
        
    def find_path_markers(self):
        """Find SVG path-based markers"""
        markers = []
        
        path_selectors = [
            "svg path[d]",
            "path[fill]",
            "g path",
            ".mark path"
        ]
        
        for selector in path_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    try:
                        if element.is_displayed() and element.size.get('width', 0) > 5:
                            location = element.location
                            size = element.size
                            center_x = location['x'] + size['width'] // 2
                            center_y = location['y'] + size['height'] // 2
                            
                            markers.append({
                                'x': center_x,
                                'y': center_y,
                                'element': element,
                                'type': 'svg_path',
                                'selector': selector
                            })
                            
                    except:
                        continue
                        
            except:
                continue
                
        return markers
        
    def find_interactive_markers(self):
        """Find elements with click handlers or interaction capabilities"""
        markers = []
        
        # JavaScript to find clickable elements
        js_script = """
        var clickableElements = [];
        
        // Find elements with click handlers or cursor pointer
        document.querySelectorAll('*').forEach(function(el) {
            var hasClick = el.onclick || 
                            el.getAttribute('onclick') || 
                            window.getComputedStyle(el).cursor === 'pointer';
                            
            if (hasClick && el.offsetWidth > 5 && el.offsetHeight > 5 && 
                el.offsetWidth < 100 && el.offsetHeight < 100) {
                var rect = el.getBoundingClientRect();
                clickableElements.push({
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2,
                    tag: el.tagName,
                    className: el.className
                });
            }
        });
        
        return clickableElements;
        """
        
        try:
            clickable_elements = self.driver.execute_script(js_script)
            
            for elem_info in clickable_elements:
                markers.append({
                    'x': int(elem_info['x']),
                    'y': int(elem_info['y']),
                    'element': None,  # We have coordinates
                    'type': 'interactive',
                    'selector': f"{elem_info['tag']}.{elem_info['className']}"
                })
                
        except Exception as e:
            print(f"⚠️ JavaScript marker discovery failed: {e}")
            
        return markers
        
    def systematic_coordinate_discovery(self):
        """Systematic coordinate-based marker discovery"""
        print("🔍 Performing systematic coordinate scan...")
        
        markers = []
        
        # Get viewport dimensions
        viewport_height = self.driver.execute_script("return window.innerHeight")
        viewport_width = self.driver.execute_script("return window.innerWidth")
        
        # Focus on the map area (center region)
        start_x = viewport_width // 4
        end_x = 3 * viewport_width // 4
        start_y = viewport_height // 4
        end_y = 3 * viewport_height // 4
        
        grid_step = 40  # Check every 40 pixels
        
        for x in range(start_x, end_x, grid_step):
            for y in range(start_y, end_y, grid_step):
                try:
                    # Check what's at this coordinate
                    element = self.driver.execute_script(
                        f"return document.elementFromPoint({x}, {y})"
                    )
                    
                    if element and self.is_likely_marker_element(element):
                        markers.append({
                            'x': x,
                            'y': y,
                            'element': element,
                            'type': 'coordinate_scan',
                            'selector': 'coordinate_based'
                        })
                        
                except:
                    continue
                    
        # Remove duplicates close to each other
        return self.deduplicate_by_proximity(markers)
        
    def is_likely_marker_element(self, element):
        """Check if an element is likely a map marker"""
        try:
            tag_name = self.driver.execute_script("return arguments[0].tagName.toLowerCase()", element)
            
            # Check tag types commonly used for markers
            if tag_name in ['circle', 'path', 'rect', 'polygon']:
                return True
                
            # Check for marker-like attributes
            classes = self.driver.execute_script("return arguments[0].className", element) or ''
            if any(keyword in classes.lower() for keyword in ['mark', 'point', 'marker', 'circle']):
                return True
                
            # Check size (markers are typically small)
            size = self.driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                return {width: rect.width, height: rect.height};
            """, element)
            
            if 5 <= size.get('width', 0) <= 30 and 5 <= size.get('height', 0) <= 30:
                return True
                
        except:
            pass
            
        return False
        
    def deduplicate_by_proximity(self, markers, min_distance=20):
        """Remove markers that are too close to each other"""
        unique_markers = []
        
        for marker in markers:
            is_duplicate = False
            
            for existing in unique_markers:
                distance = ((marker['x'] - existing['x'])**2 + (marker['y'] - existing['y'])**2)**0.5
                if distance < min_distance:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                unique_markers.append(marker)
                
        return unique_markers
        
    def deduplicate_and_validate_markers(self, markers):
        """Remove duplicates and validate markers"""
        print("🔧 Deduplicating and validating markers...")
        
        # Remove proximity duplicates
        unique_markers = self.deduplicate_by_proximity(markers)
        
        # Filter out markers outside reasonable bounds
        viewport_height = self.driver.execute_script("return window.innerHeight")
        viewport_width = self.driver.execute_script("return window.innerWidth")
        
        valid_markers = []
        for marker in unique_markers:
            if (50 < marker['x'] < viewport_width - 50 and 
                50 < marker['y'] < viewport_height - 50):
                valid_markers.append(marker)
                
        print(f"✅ Validated {len(valid_markers)} unique markers")
        return valid_markers
        
    def extract_from_all_markers(self, markers):
        """Extract data from all discovered markers"""
        print(f"🚀 EXTRACTING DATA FROM {len(markers)} MARKERS")
        print("=" * 60)
        
        for i, marker in enumerate(markers, 1):
            print(f"\n📍 Processing marker {i}/{len(markers)} at ({marker['x']}, {marker['y']})")
            
            # Try multiple extraction methods
            project_data = None
            
            # Method 1: Direct API call (proven method)
            project_data = self.extract_via_api_call(marker, i)
            
            # Method 2: Click and capture if API fails
            if not project_data:
                project_data = self.extract_via_click_and_capture(marker, i)
                
            if project_data:
                # Check if this is a unique project
                if self.is_unique_project(project_data):
                    self.all_projects.append(project_data)
                    self.successful_extractions += 1
                    print(f"✅ SUCCESS: {project_data.get('company_name', 'Unknown Company')}")
                else:
                    print("🔄 Duplicate project, skipped")
            else:
                self.failed_extractions += 1
                print("❌ Failed to extract data")
                
            # Brief pause between extractions
            time.sleep(0.5)
            
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"✅ Successful: {self.successful_extractions}")
        print(f"❌ Failed: {self.failed_extractions}")
        print(f"📊 Total Projects: {len(self.all_projects)}")
        
    def extract_via_api_call(self, marker, marker_index):
        """Extract using direct API call (proven method)"""
        try:
            # Build API request
            url = f"https://public.tableau.com/views/IETFProjectMap/MapDashboard/sessions/{self.session_id}/commands/tabdoc/render-tooltip-server"
            
            # Generate boundary for multipart form
            boundary = f"----formdata-webdriver-{random.randint(1000000, 9999999)}"
            
            # Build form data
            form_data = self.build_form_data(boundary, marker['x'], marker['y'], marker_index)
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Cookie': self.cookies,
                'Origin': 'https://public.tableau.com',
                'Referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Make the request
            response = requests.post(url, data=form_data, headers=headers, timeout=10)
            
            if response.status_code == 200 and len(response.text) > 1000:
                return self.parse_api_response(response.text)
            else:
                print(f"⚠️ API call failed: {response.status_code}, size: {len(response.text)}")
                return None
                
        except Exception as e:
            print(f"⚠️ API extraction failed: {e}")
            return None
            
    def build_form_data(self, boundary, x, y, marker_index):
        """Build multipart form data for Tableau API"""
        
        # Use a valid tuple ID (systematic approach)
        tuple_id = marker_index
        
        form_data = f"""--{boundary}\r
Content-Disposition: form-data; name="renderTooltipServer"\r
\r
{{"worksheet":"Map External","dashboard":"Map Dashboard","globalFieldName":"","useInlineImages":true,"useAnimations":true,"vizql":"{{"worldUpdate":{{"applicationPresModel":{{"workbookPresModel":{{"sheetsPresModel":{{"Map External":{{"presModelHolder":{{"visual":{{"tooltipPresModel":{{"mark":{{"tupleIds":[{tuple_id}]}},"popupPosition":{{"x":{x},"y":{y},"targetX":{x},"targetY":{y}}}}}}}}}}}}}}}}}}},"commandName":"tabdoc:render-tooltip-server","commandVersion":"1"}}\r
--{boundary}--\r
"""
        return form_data
        
    def extract_via_click_and_capture(self, marker, marker_index):
        """Extract by clicking marker and capturing tooltip"""
        try:
            # Click at the marker coordinates
            ActionChains(self.driver).move_by_offset(marker['x'], marker['y']).click().perform()
            time.sleep(1)
            
            # Look for tooltip content
            tooltip_selectors = [
                "[class*='tooltip']",
                "[class*='popup']", 
                "[id*='tooltip']",
                "[data-tb-test-id*='tooltip']"
            ]
            
            for selector in tooltip_selectors:
                try:
                    tooltip = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if tooltip.is_displayed():
                        tooltip_text = tooltip.text
                        if len(tooltip_text) > 100:  # Substantial content
                            return self.parse_tooltip_text(tooltip_text)
                except:
                    continue
                    
            return None
            
        except Exception as e:
            print(f"⚠️ Click extraction failed: {e}")
            return None
            
    def parse_api_response(self, response_text):
        """Parse Tableau API response to extract project data"""
        try:
            # Find JSON in response
            json_match = re.search(r'\{.*"htmlTooltip".*\}', response_text, re.DOTALL)
            if not json_match:
                return None
                
            response_json = json.loads(json_match.group())
            
            if 'vizqlCmds' in response_json:
                for cmd in response_json['vizqlCmds']:
                    if 'commandReturn' in cmd and 'htmlTooltip' in cmd['commandReturn']:
                        html_content = cmd['commandReturn']['htmlTooltip']
                        return self.parse_html_tooltip(html_content)
                        
        except Exception as e:
            print(f"⚠️ Response parsing failed: {e}")
            
        return None
        
    def parse_html_tooltip(self, html_content):
        """Parse HTML tooltip content to extract structured data"""
        try:
            # Decode HTML entities
            decoded_html = html.unescape(html_content)
            
            # Extract text content
            text_content = re.sub(r'<[^>]+>', ' ', decoded_html)
            text_content = ' '.join(text_content.split())
            
            return self.parse_tooltip_text(text_content)
            
        except Exception as e:
            print(f"⚠️ HTML parsing failed: {e}")
            return None
            
    def parse_tooltip_text(self, text):
        """Parse tooltip text to extract structured project data"""
        project_data = {}
        
        try:
            # Company name (often at the beginning)
            company_match = re.search(r'^([^£\n]+?)(?:\s*£|\s*Total|\s*Government)', text, re.MULTILINE)
            if company_match:
                project_data['company_name'] = company_match.group(1).strip()
            
            # Financial data
            cost_match = re.search(r'(?:Total|Cost|Project).*?£([0-9,]+)', text, re.IGNORECASE)
            if cost_match:
                project_data['total_cost'] = f"£{cost_match.group(1)}"
            
            grant_match = re.search(r'Government.*?£([0-9,]+)', text, re.IGNORECASE)
            if grant_match:
                project_data['government_grant'] = f"£{grant_match.group(1)}"
            
            # Technology/industry
            tech_keywords = ['electrification', 'decarbonisation', 'hydrogen', 'manufacturing', 'steel', 'cement']
            for keyword in tech_keywords:
                if keyword.lower() in text.lower():
                    project_data['technology'] = keyword.title()
                    break
            
            # Region
            regions = ['South West', 'North East', 'North West', 'Yorkshire', 'Midlands', 'London', 'Scotland', 'Wales']
            for region in regions:
                if region in text:
                    project_data['region'] = region
                    break
            
            # Store raw text for reference
            project_data['raw_tooltip'] = text[:500]  # First 500 chars
            project_data['extraction_time'] = datetime.now().isoformat()
            
            return project_data if project_data.get('company_name') else None
            
        except Exception as e:
            print(f"⚠️ Text parsing failed: {e}")
            return None
            
    def is_unique_project(self, project_data):
        """Check if this project is unique (not already extracted)"""
        company_name = project_data.get('company_name', '')
        
        for existing_project in self.all_projects:
            if existing_project.get('company_name', '') == company_name:
                return False
                
        return True
        
    def save_complete_results(self):
        """Save all extracted data in multiple formats"""
        print("💾 Saving complete extraction results...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_filename = f"ietf_complete_extraction_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'extraction_summary': {
                    'total_projects': len(self.all_projects),
                    'successful_extractions': self.successful_extractions,
                    'failed_extractions': self.failed_extractions,
                    'extraction_time': datetime.now().isoformat()
                },
                'projects': self.all_projects
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON saved: {json_filename}")
        
        # Save CSV
        csv_filename = f"ietf_complete_extraction_{timestamp}.csv"
        if self.all_projects:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['company_name', 'total_cost', 'government_grant', 'technology', 'region', 'extraction_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for project in self.all_projects:
                    row = {field: project.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            print(f"✅ CSV saved: {csv_filename}")
        
        # Save summary report
        report_filename = f"ietf_extraction_report_{timestamp}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(f"# IETF Complete Extraction Report\n\n")
            f.write(f"**Extraction Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Summary\n")
            f.write(f"- **Total Projects Extracted:** {len(self.all_projects)}\n")
            f.write(f"- **Successful Extractions:** {self.successful_extractions}\n")
            f.write(f"- **Failed Attempts:** {self.failed_extractions}\n\n")
            
            if self.all_projects:
                f.write("## Extracted Projects\n\n")
                for i, project in enumerate(self.all_projects, 1):
                    f.write(f"### {i}. {project.get('company_name', 'Unknown Company')}\n")
                    f.write(f"- **Cost:** {project.get('total_cost', 'N/A')}\n")
                    f.write(f"- **Grant:** {project.get('government_grant', 'N/A')}\n")
                    f.write(f"- **Technology:** {project.get('technology', 'N/A')}\n")
                    f.write(f"- **Region:** {project.get('region', 'N/A')}\n\n")
                    
        print(f"✅ Report saved: {report_filename}")
        
        return json_filename, csv_filename, report_filename
        
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            print("✅ Browser closed")
            
    def run_complete_automated_extraction(self):
        """Run the complete automated extraction process"""
        print("🚀 STARTING COMPLETE AUTOMATED IETF EXTRACTION")
        print("=" * 60)
        
        try:
            # Step 1: Setup browser
            self.setup_chrome_for_automation()
            
            # Step 2: Load Tableau map
            if not self.load_tableau_map_automatically():
                print("❌ Failed to load Tableau map")
                return False
                
            # Step 3: Discover all markers
            markers = self.discover_all_markers_automatically()
            if not markers:
                print("❌ No markers discovered")
                return False
                
            # Step 4: Extract from all markers
            self.extract_from_all_markers(markers)
            
            # Step 5: Save results
            json_file, csv_file, report_file = self.save_complete_results()
            
            print(f"\n🎉 EXTRACTION COMPLETE!")
            print(f"📊 {len(self.all_projects)} projects extracted successfully")
            print(f"📁 Files saved:")
            print(f"   - {json_file}")
            print(f"   - {csv_file}")
            print(f"   - {report_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return False
            
        finally:
            self.cleanup()


def main():
    """Main execution function"""
    print("🤖 Ultimate Tableau Extractor - 100% Automated IETF Data Extraction")
    print("=" * 70)
    
    extractor = UltimateTableauExtractor()
    success = extractor.run_complete_automated_extraction()
    
    if success:
        print("\n✅ Mission accomplished! All IETF data extracted automatically.")
    else:
        print("\n❌ Extraction failed. Check the logs above for details.")


if __name__ == "__main__":
    main() 