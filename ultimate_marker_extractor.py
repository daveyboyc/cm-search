#!/usr/bin/env python3
"""
Ultimate IETF Marker Extractor - The definitive solution
Handles session extraction, real marker discovery, and proven API calls
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

class UltimateMarkerExtractor:
    def __init__(self):
        self.driver = None
        self.session_id = None
        self.cookies = None
        self.all_projects = []
        self.processed_tuples = set()
        self.base_url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard"
        
    def setup_driver(self):
        """Setup Chrome with optimal settings"""
        print("🎯 Setting up ultimate Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print("✅ Ultimate driver ready")
        
    def load_and_extract_session(self):
        """Load page and properly extract session information"""
        print("🌐 Loading Tableau page and extracting session...")
        
        # Load main page first
        self.driver.get(self.base_url)
        time.sleep(10)
        
        # Extract cookies
        cookies = self.driver.get_cookies()
        self.cookies = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print(f"✅ Extracted {len(cookies)} cookies")
        
        # Find session ID with comprehensive patterns
        page_source = self.driver.page_source
        
        # Multiple session extraction patterns
        session_patterns = [
            r'"sessionId"\s*:\s*"([^"]+)"',
            r'sessionId["\']?\s*[:=]\s*["\']?([A-F0-9]{32}-\d+:\d+)',
            r'sessions/([A-F0-9]{32}-\d+:\d+)',
            r'&sessionId=([A-F0-9-]+)',
            r'bootstrap.*sessions/([A-F0-9]{32}-\d+:\d+)',
            r'"session_id"\s*:\s*"([^"]+)"'
        ]
        
        for pattern in session_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                # Take the first valid match
                for match in matches:
                    if len(match) > 20:  # Valid session IDs are long
                        self.session_id = match
                        print(f"✅ Session ID found: {self.session_id[:30]}...")
                        break
                if self.session_id:
                    break
        
        if not self.session_id:
            print("⚠️ Session ID not found in page source")
            print("🔍 Attempting iframe-based session extraction...")
            
            # Try to extract from iframe
            try:
                iframe = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                self.driver.switch_to.frame(iframe)
                time.sleep(8)
                
                # Get iframe source
                iframe_source = self.driver.page_source
                for pattern in session_patterns:
                    matches = re.findall(pattern, iframe_source, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            if len(match) > 20:
                                self.session_id = match
                                print(f"✅ Session ID found in iframe: {self.session_id[:30]}...")
                                break
                        if self.session_id:
                            break
                
                # Stay in iframe for marker discovery
                print("✅ Staying in iframe context for marker discovery")
                
            except Exception as e:
                print(f"⚠️ Failed to switch to iframe: {e}")
                return False
        
        return True
    
    def discover_real_map_markers(self):
        """Discover actual map markers using multiple strategies"""
        print("🗺️ Discovering real map markers...")
        
        markers = []
        
        # Wait for map to fully load
        time.sleep(8)
        
        # Strategy 1: Look for SVG circles (most common for Tableau maps)
        try:
            circles = self.driver.find_elements(By.CSS_SELECTOR, "circle")
            print(f"🔍 Found {len(circles)} circle elements")
            
            for circle in circles:
                try:
                    if (circle.is_displayed() and 
                        circle.size['width'] > 5 and circle.size['width'] < 50):
                        
                        location = circle.location_once_scrolled_into_view
                        
                        # Filter for map area (not UI elements)
                        if (location['x'] > 100 and location['x'] < 900 and
                            location['y'] > 100 and location['y'] < 700):
                            
                            markers.append({
                                'x': location['x'] + circle.size['width'] // 2,
                                'y': location['y'] + circle.size['height'] // 2,
                                'element': circle,
                                'type': 'map_circle',
                                'size': circle.size
                            })
                            
                except Exception as e:
                    continue
                    
            print(f"✅ Found {len(markers)} potential map circles")
            
        except Exception as e:
            print(f"⚠️ Circle discovery failed: {e}")
        
        # Strategy 2: Strategic coordinate testing
        test_coordinates = [
            # UK map strategic locations
            (300, 200), (400, 250), (500, 300), (600, 280), (350, 350),
            (450, 200), (550, 320), (380, 400), (480, 180), (320, 300),
            (420, 350), (520, 250), (620, 400), (280, 380), (580, 200),
            (360, 450), (460, 320), (560, 180), (660, 350), (240, 250)
        ]
        
        print("🎯 Testing strategic coordinates...")
        
        for x, y in test_coordinates:
            try:
                element = self.driver.execute_script(f"""
                    var el = document.elementFromPoint({x}, {y});
                    if (el && el.tagName && (el.tagName.toLowerCase() === 'circle' || el.tagName.toLowerCase() === 'path')) {{
                        return {{
                            tag: el.tagName,
                            x: {x},
                            y: {y},
                            width: el.getBoundingClientRect().width,
                            height: el.getBoundingClientRect().height
                        }};
                    }}
                    return null;
                """)
                
                if element and element['width'] > 5 and element['width'] < 50:
                    markers.append({
                        'x': x,
                        'y': y,
                        'element': None,
                        'type': 'coordinate_test',
                        'size': {'width': element['width'], 'height': element['height']}
                    })
                    
            except Exception:
                continue
        
        # Remove duplicates
        unique_markers = self.remove_duplicate_markers(markers)
        print(f"🎯 Total unique markers discovered: {len(unique_markers)}")
        
        return unique_markers
    
    def remove_duplicate_markers(self, markers):
        """Remove duplicate markers based on proximity"""
        if not markers:
            return []
        
        unique_markers = []
        min_distance = 30
        
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
    
    def extract_data_from_markers(self, markers):
        """Extract data from all markers using the proven API method"""
        print(f"🚀 Extracting data from {len(markers)} markers...")
        
        if not self.session_id:
            print("❌ No session ID available for API calls")
            return 0
        
        successful_extractions = 0
        
        for i, marker in enumerate(markers):
            print(f"\n🎯 Processing marker {i+1}/{len(markers)} at ({marker['x']}, {marker['y']})...")
            
            project_data = self.extract_via_tableau_api(marker, i+1)
            
            if project_data:
                project_data['marker_index'] = i + 1
                project_data['coordinates'] = {'x': marker['x'], 'y': marker['y']}
                project_data['discovery_method'] = marker['type']
                
                tuple_id = project_data.get('tuple_id') or project_data.get('api_tuple_id') or f"marker_{i+1}"
                
                if tuple_id not in self.processed_tuples:
                    self.all_projects.append(project_data)
                    self.processed_tuples.add(tuple_id)
                    successful_extractions += 1
                    
                    company = project_data.get('company_name', 'Unknown Company')
                    cost = project_data.get('total_cost', 'N/A')
                    print(f"✅ SUCCESS #{successful_extractions}: {company} - £{cost}")
                else:
                    print(f"⚠️ Duplicate project detected")
            else:
                print(f"❌ No data extracted from marker {i+1}")
            
            time.sleep(2)  # Rate limiting
        
        print(f"\n🎉 EXTRACTION COMPLETE: {successful_extractions} unique projects found!")
        return successful_extractions
    
    def extract_via_tableau_api(self, marker, marker_index):
        """Extract data using proven Tableau API method"""
        try:
            url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{self.session_id}/commands/tabsrv/render-tooltip-server"
            
            headers = {
                'accept': 'text/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': f'multipart/form-data; boundary=ultimate{marker_index}',
                'cookie': self.cookies,
                'origin': 'https://public.tableau.com',
                'referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            boundary = f"ultimate{marker_index}"
            data = f"""--{boundary}\r
Content-Disposition: form-data; name="worksheet"\r
\r
Map External\r
--{boundary}\r
Content-Disposition: form-data; name="dashboard"\r
\r
Map Dashboard\r
--{boundary}\r
Content-Disposition: form-data; name="tupleIds"\r
\r
[{marker_index}]\r
--{boundary}\r
Content-Disposition: form-data; name="vizRegionRect"\r
\r
{{"r":"viz","x":{marker['x']},"y":{marker['y']},"w":0,"h":0,"fieldVector":null}}\r
--{boundary}\r
Content-Disposition: form-data; name="allowHoverActions"\r
\r
false\r
--{boundary}\r
Content-Disposition: form-data; name="allowPromptText"\r
\r
true\r
--{boundary}\r
Content-Disposition: form-data; name="allowWork"\r
\r
false\r
--{boundary}\r
Content-Disposition: form-data; name="useInlineImages"\r
\r
true\r
--{boundary}\r
Content-Disposition: form-data; name="telemetryCommandId"\r
\r
ultimate{marker_index}extract\r
--{boundary}--\r
"""
            
            response = requests.post(url, headers=headers, data=data, timeout=15)
            
            if response.status_code == 200 and len(response.text) > 1000:
                return self.parse_tableau_response(response.text)
            elif response.status_code == 410:
                print(f"⚠️ Session expired (410)")
            else:
                print(f"⚠️ API request failed with status {response.status_code}")
            
        except Exception as e:
            print(f"⚠️ API extraction failed: {e}")
        
        return None
    
    def parse_tableau_response(self, response_text):
        """Parse Tableau API response to extract project data"""
        try:
            response_data = json.loads(response_text)
            cmd_result = response_data["vqlCmdResponse"]["cmdResultList"][0]
            tooltip_json = cmd_result["commandReturn"]["tooltipText"]
            tooltip_data = json.loads(tooltip_json)
            
            if tooltip_data.get("isEmpty", True):
                return None
            
            html_tooltip = tooltip_data["htmlTooltip"]
            project_data = self.parse_html_tooltip(html_tooltip)
            
            if project_data:
                project_data['api_tuple_id'] = tooltip_data.get("tupleId")
                
                # Extract government URL
                url_match = re.search(r'https://www\.gov\.uk[^"\\]+', html_tooltip)
                if url_match:
                    gov_url = url_match.group(0).replace('\\', '').replace('""', '')
                    project_data['government_url'] = unquote(gov_url)
            
            return project_data
            
        except Exception as e:
            print(f"⚠️ Response parsing failed: {e}")
            return None
    
    def parse_html_tooltip(self, html_content):
        """Parse HTML tooltip to extract structured project data"""
        clean_html = html.unescape(html_content)
        text_content = re.sub(r'</div>', '\n', clean_html)
        text_content = re.sub(r'<br[^>]*>', '\n', text_content)
        text_content = re.sub(r'<[^>]+>', '', text_content)
        
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        project_data = {}
        
        for line in lines:
            if re.search(r'(Ltd|Limited|PLC|Group|Company)', line, re.IGNORECASE) and not project_data.get('company_name'):
                project_data['company_name'] = line
            elif line.startswith('Industry:'):
                project_data['industry'] = line.replace('Industry:', '').strip()
            elif line.startswith('Competition:'):
                project_data['competition'] = line.replace('Competition:', '').strip()
            elif line.startswith('Region:'):
                project_data['region'] = line.replace('Region:', '').strip()
            elif line.startswith('Project type:'):
                project_data['project_type'] = line.replace('Project type:', '').strip()
            elif line.startswith('Technology:'):
                project_data['technology'] = line.replace('Technology:', '').strip()
            elif line.startswith('Solution:'):
                project_data['solution'] = line.replace('Solution:', '').strip()
            elif line.startswith('Total cost:'):
                cost_match = re.search(r'£?([0-9,]+)', line)
                if cost_match:
                    project_data['total_cost'] = cost_match.group(1)
            elif line.startswith('Total grant:'):
                grant_match = re.search(r'£?([0-9,]+)', line)
                if grant_match:
                    project_data['total_grant'] = grant_match.group(1)
            elif len(line) > 80 and 'description' not in project_data:
                project_data['description'] = line
        
        return project_data if len(project_data) >= 3 else None
    
    def save_ultimate_results(self):
        """Save comprehensive results"""
        print("💾 Saving ultimate extraction results...")
        
        with open("ultimate_ietf_extraction.json", "w", encoding="utf-8") as f:
            json.dump(self.all_projects, f, indent=2, ensure_ascii=False)
        
        report = self.generate_ultimate_report()
        
        with open("ultimate_ietf_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        print("💾 All results saved successfully")
    
    def generate_ultimate_report(self):
        """Generate comprehensive analysis report"""
        total_projects = len(self.all_projects)
        
        if total_projects == 0:
            return """# Ultimate IETF Extraction Report

## ❌ No Projects Extracted

Unfortunately, no project data was successfully extracted. This could be due to:

1. **Session Issues**: The Tableau session may have expired or been invalid
2. **Marker Detection**: The discovered elements may not have been actual project markers
3. **API Changes**: Tableau may have changed their API structure
4. **Rate Limiting**: Requests may have been blocked or throttled

## Next Steps

To resolve this, you need to:
1. Open the IETF map in your browser manually
2. Click on a marker to see tooltip data
3. Capture the network request using browser dev tools
4. Copy the working cURL command and extract the session ID
5. Use that session in the extractor

The issue is likely that the automatic session detection isn't working properly.
"""
        
        # Generate full report for successful extractions
        total_cost = sum(int(p.get('total_cost', '0').replace(',', '')) for p in self.all_projects if p.get('total_cost', '').replace(',', '').isdigit())
        total_grant = sum(int(p.get('total_grant', '0').replace(',', '')) for p in self.all_projects if p.get('total_grant', '').replace(',', '').isdigit())
        
        report = f"""# Ultimate IETF Extraction Report

## 🎯 Extraction Summary
- **Total Projects Extracted:** {total_projects}
- **Total Investment Value:** £{total_cost:,}
- **Total Government Grants:** £{total_grant:,}
- **Average Project Value:** £{total_cost // total_projects if total_projects > 0 else 0:,}

## 📋 Complete Project Database

"""
        
        for i, project in enumerate(self.all_projects, 1):
            company = project.get('company_name', 'Unknown Company')
            cost = project.get('total_cost', 'N/A')
            grant = project.get('total_grant', 'N/A')
            region = project.get('region', 'Unknown')
            
            report += f"### {i}. {company}\n"
            report += f"- **Total Cost:** £{cost}\n"
            report += f"- **Grant:** £{grant}\n"
            report += f"- **Region:** {region}\n"
            
            if project.get('industry'):
                report += f"- **Industry:** {project['industry']}\n"
            if project.get('technology'):
                report += f"- **Technology:** {project['technology']}\n"
            if project.get('government_url'):
                report += f"- **Government URL:** {project['government_url']}\n"
            
            report += "\n"
        
        return report
    
    def run_ultimate_extraction(self):
        """Run the complete ultimate extraction process"""
        print("🏆 ULTIMATE IETF MARKER EXTRACTION")
        print("=" * 60)
        print("🎯 The definitive solution for automated marker discovery")
        print()
        
        try:
            self.setup_driver()
            
            if not self.load_and_extract_session():
                print("❌ Failed to load page or extract session")
                return False
            
            markers = self.discover_real_map_markers()
            if not markers:
                print("❌ No real map markers discovered")
                return False
            
            print(f"\n🎯 DISCOVERED {len(markers)} REAL MAP MARKERS")
            print("🚀 Beginning ultimate data extraction...")
            
            successful_count = self.extract_data_from_markers(markers)
            self.save_ultimate_results()
            
            if successful_count > 0:
                print(f"\n🏆 ULTIMATE EXTRACTION SUCCESS!")
                print(f"✅ Successfully extracted {successful_count} unique projects")
                return True
            else:
                print(f"\n⚠️ No projects extracted - check ultimate report")
                return False
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            return False
            
        finally:
            if self.driver:
                print("🔄 Cleaning up...")
                self.driver.quit()

if __name__ == "__main__":
    print("🏆 ULTIMATE IETF EXTRACTION SYSTEM")
    print("The final solution for comprehensive marker discovery and data extraction")
    print()
    
    extractor = UltimateMarkerExtractor()
    success = extractor.run_ultimate_extraction()
    
    if success:
        print("\n🏆 Ultimate extraction completed successfully!")
    else:
        print("\n📊 Extraction completed - check report for analysis") 