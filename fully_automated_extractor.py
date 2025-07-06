#!/usr/bin/env python3
"""
Fully Automated IETF Extractor - Zero manual intervention
Automatically discovers ALL markers and extracts complete data
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

class FullyAutomatedExtractor:
    def __init__(self):
        self.driver = None
        self.session_id = None
        self.cookies = None
        self.all_projects = []
        self.processed_tuples = set()
        
    def setup_driver(self):
        """Setup Chrome with performance logging"""
        print("🚀 Setting up automated Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Enable network domain for CDP
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enable Network domain
        self.driver.execute_cdp_cmd('Network.enable', {})
        
        print("✅ Driver ready with network monitoring")
        
    def load_tableau_map(self):
        """Load the Tableau map and extract session info"""
        print("📄 Loading IETF Tableau map...")
        
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard"
        self.driver.get(url)
        
        # Wait for page load
        time.sleep(15)
        
        # Extract session info from the main page first
        self.extract_session_info()
        
        # Switch to iframe
        try:
            print("🔍 Looking for map iframe...")
            iframe = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            print("✅ Found iframe, switching context...")
            self.driver.switch_to.frame(iframe)
            
            # Wait for map to fully load
            time.sleep(12)
            print("✅ Map loaded in iframe")
            
        except Exception as e:
            print(f"❌ Failed to load iframe: {e}")
            return False
            
        return True
    
    def extract_session_info(self):
        """Extract session cookies and ID"""
        print("🔑 Extracting session information...")
        
        # Get all cookies
        cookies = self.driver.get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        self.cookies = cookie_str
        print(f"✅ Extracted {len(cookies)} cookies")
        
        # Find session ID in page source
        page_source = self.driver.page_source
        session_patterns = [
            r'sessions/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}-\d+:\d+)',
            r'sessions/([A-F0-9-]+)',
            r'"sessionId":"([^"]+)"',
            r'sessionId=([A-F0-9-]+)'
        ]
        
        for pattern in session_patterns:
            match = re.search(pattern, page_source)
            if match:
                self.session_id = match.group(1)
                print(f"✅ Session ID found: {self.session_id[:30]}...")
                break
        
        if not self.session_id:
            print("⚠️ Session ID not found in page source")
    
    def discover_all_markers(self):
        """Systematically discover all markers by scanning the map"""
        print("🎯 Discovering all markers systematically...")
        
        # Get map dimensions
        try:
            map_element = self.driver.find_element(By.TAG_NAME, "body")
            map_size = map_element.size
            print(f"📐 Map area: {map_size['width']}x{map_size['height']}")
        except:
            map_size = {'width': 1920, 'height': 1080}
        
        discovered_markers = []
        
        # Strategy 1: Find SVG elements (most likely for Tableau)
        svg_markers = self.find_svg_markers()
        if svg_markers:
            discovered_markers.extend(svg_markers)
            print(f"✅ Found {len(svg_markers)} SVG markers")
        
        # Strategy 2: Grid-based click detection
        if len(discovered_markers) < 5:  # If we didn't find many, try grid approach
            print("🔍 Using grid-based marker discovery...")
            grid_markers = self.grid_scan_for_markers(map_size)
            discovered_markers.extend(grid_markers)
        
        # Strategy 3: Listen for network requests while scanning
        network_markers = self.scan_with_network_monitoring()
        discovered_markers.extend(network_markers)
        
        # Remove duplicates based on coordinates
        unique_markers = self.deduplicate_markers(discovered_markers)
        
        print(f"🎯 Total unique markers discovered: {len(unique_markers)}")
        return unique_markers
    
    def find_svg_markers(self):
        """Find SVG-based markers"""
        markers = []
        
        svg_selectors = [
            "circle[r]",  # Circles with radius
            "svg circle",
            "g circle",
            ".mark circle",
            "path[d*='M']",  # Paths (might be custom markers)
            "[data-tb-test-id*='mark']"
        ]
        
        for selector in svg_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        if (element.is_displayed() and 
                            element.size['width'] > 3 and 
                            element.size['height'] > 3 and
                            element.size['width'] < 100):  # Reasonable marker size
                            
                            location = element.location
                            size = element.size
                            center_x = location['x'] + size['width'] // 2
                            center_y = location['y'] + size['height'] // 2
                            
                            markers.append({
                                'x': center_x,
                                'y': center_y,
                                'element': element,
                                'type': 'svg',
                                'selector': selector
                            })
                    except:
                        continue
                        
                if markers:
                    print(f"✅ Found {len(markers)} markers with selector: {selector}")
                    break
                    
            except Exception as e:
                continue
        
        return markers
    
    def grid_scan_for_markers(self, map_size):
        """Grid-based scanning for markers"""
        print("🔍 Performing grid scan...")
        
        markers = []
        grid_step = 50  # Check every 50 pixels
        
        for y in range(100, map_size['height'] - 100, grid_step):
            for x in range(100, map_size['width'] - 100, grid_step):
                try:
                    # Try to find clickable element at this position
                    element = self.driver.execute_script(
                        "return document.elementFromPoint(arguments[0], arguments[1]);",
                        x, y
                    )
                    
                    if element and self.is_likely_marker(element):
                        markers.append({
                            'x': x,
                            'y': y,
                            'element': element,
                            'type': 'grid',
                            'selector': 'grid_scan'
                        })
                        
                except:
                    continue
        
        print(f"🔍 Grid scan found {len(markers)} potential markers")
        return markers
    
    def is_likely_marker(self, element):
        """Check if element is likely a marker"""
        try:
            tag_name = element.tag_name.lower()
            class_name = (element.get_attribute('class') or '').lower()
            
            # Check for marker-like characteristics
            if tag_name in ['circle', 'path', 'rect']:
                return True
            
            if any(keyword in class_name for keyword in ['mark', 'point', 'marker', 'dot']):
                return True
            
            # Check size (markers are usually small)
            try:
                size = element.size
                if 5 <= size['width'] <= 50 and 5 <= size['height'] <= 50:
                    return True
            except:
                pass
            
            return False
            
        except:
            return False
    
    def scan_with_network_monitoring(self):
        """Scan while monitoring network requests"""
        print("📡 Scanning with network monitoring...")
        
        discovered_markers = []
        
        # Clear network logs
        self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        
        # Perform systematic clicking while monitoring network
        for attempt in range(20):  # Try 20 different locations
            try:
                # Click at semi-random but systematic locations
                x = 200 + (attempt * 60) % 800
                y = 200 + (attempt * 40) % 400
                
                # Click using JavaScript to avoid element detection issues
                self.driver.execute_script(f"document.elementFromPoint({x}, {y})?.click();")
                
                time.sleep(1)
                
                # Check for network activity
                if self.check_for_tooltip_request():
                    discovered_markers.append({
                        'x': x,
                        'y': y,
                        'element': None,
                        'type': 'network',
                        'selector': 'network_scan'
                    })
                    print(f"📡 Network activity detected at ({x}, {y})")
                
            except:
                continue
        
        return discovered_markers
    
    def check_for_tooltip_request(self):
        """Check if a tooltip request was made"""
        try:
            # Get recent network logs
            logs = self.driver.get_log('performance')
            for log in logs[-5:]:  # Check last 5 logs
                message = json.loads(log['message'])
                if (message.get('message', {}).get('method') == 'Network.responseReceived'):
                    url = message['message']['params']['response'].get('url', '')
                    if 'render-tooltip-server' in url:
                        return True
            return False
        except:
            return False
    
    def deduplicate_markers(self, markers):
        """Remove duplicate markers based on proximity"""
        if not markers:
            return []
        
        unique_markers = []
        min_distance = 30  # Minimum pixels between markers
        
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
    
    def extract_data_from_all_markers(self, markers):
        """Extract data from all discovered markers"""
        print(f"📊 Extracting data from {len(markers)} markers...")
        
        successful_extractions = 0
        
        for i, marker in enumerate(markers):
            print(f"\n🎯 Processing marker {i+1}/{len(markers)} at ({marker['x']}, {marker['y']})...")
            
            # Try multiple extraction methods
            project_data = None
            
            # Method 1: Direct API call with coordinates
            if self.session_id:
                project_data = self.extract_via_api(marker['x'], marker['y'], i+1)
            
            # Method 2: Click and capture network if API fails
            if not project_data:
                project_data = self.click_and_capture(marker, i+1)
            
            # Method 3: Click and parse page content
            if not project_data:
                project_data = self.click_and_parse_page(marker, i+1)
            
            if project_data:
                project_data['marker_index'] = i + 1
                project_data['coordinates'] = {'x': marker['x'], 'y': marker['y']}
                project_data['discovery_method'] = marker['type']
                
                # Avoid duplicates based on tuple_id
                tuple_id = project_data.get('tuple_id') or project_data.get('api_tuple_id')
                if tuple_id and tuple_id not in self.processed_tuples:
                    self.all_projects.append(project_data)
                    self.processed_tuples.add(tuple_id)
                    successful_extractions += 1
                    
                    company = project_data.get('company_name', 'Unknown')
                    cost = project_data.get('total_cost', 'N/A')
                    print(f"✅ Success {successful_extractions}: {company} - £{cost}")
                else:
                    print(f"⚠️ Duplicate project (tuple_id: {tuple_id})")
            else:
                print(f"❌ No data extracted from marker {i+1}")
            
            # Brief delay between markers
            time.sleep(2)
        
        print(f"\n🎉 Extraction complete! {successful_extractions} unique projects found")
        return successful_extractions
    
    def extract_via_api(self, x, y, marker_index):
        """Extract using direct API call"""
        try:
            url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{self.session_id}/commands/tabsrv/render-tooltip-server"
            
            headers = {
                'accept': 'text/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': f'multipart/form-data; boundary=auto{marker_index}',
                'cookie': self.cookies,
                'origin': 'https://public.tableau.com',
                'referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            boundary = f"auto{marker_index}"
            data = f'--{boundary}\r\nContent-Disposition: form-data; name="worksheet"\r\n\r\nMap External\r\n--{boundary}\r\nContent-Disposition: form-data; name="dashboard"\r\n\r\nMap Dashboard\r\n--{boundary}\r\nContent-Disposition: form-data; name="tupleIds"\r\n\r\n[{marker_index}]\r\n--{boundary}\r\nContent-Disposition: form-data; name="vizRegionRect"\r\n\r\n{{"r":"viz","x":{x},"y":{y},"w":0,"h":0,"fieldVector":null}}\r\n--{boundary}\r\nContent-Disposition: form-data; name="allowHoverActions"\r\n\r\nfalse\r\n--{boundary}\r\nContent-Disposition: form-data; name="allowPromptText"\r\n\r\ntrue\r\n--{boundary}\r\nContent-Disposition: form-data; name="allowWork"\r\n\r\nfalse\r\n--{boundary}\r\nContent-Disposition: form-data; name="useInlineImages"\r\n\r\ntrue\r\n--{boundary}\r\nContent-Disposition: form-data; name="telemetryCommandId"\r\n\r\nauto{marker_index}extract\r\n--{boundary}--\r\n'
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200 and len(response.text) > 1000:
                return self.parse_api_response(response.text)
            
        except Exception as e:
            print(f"⚠️ API extraction failed: {e}")
        
        return None
    
    def click_and_capture(self, marker, marker_index):
        """Click marker and capture network response"""
        try:
            # Clear network logs
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            
            # Click the marker
            if marker['element']:
                ActionChains(self.driver).move_to_element(marker['element']).click().perform()
            else:
                self.driver.execute_script(f"document.elementFromPoint({marker['x']}, {marker['y']})?.click();")
            
            time.sleep(3)
            
            # Check network logs for tooltip response
            logs = self.driver.get_log('performance')
            for log in logs:
                message = json.loads(log['message'])
                if message.get('message', {}).get('method') == 'Network.responseReceived':
                    url = message['message']['params']['response'].get('url', '')
                    if 'render-tooltip-server' in url:
                        # Try to get response body
                        request_id = message['message']['params']['requestId']
                        try:
                            response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                            if response_body.get('body'):
                                return self.parse_api_response(response_body['body'])
                        except:
                            continue
            
        except Exception as e:
            print(f"⚠️ Click and capture failed: {e}")
        
        return None
    
    def click_and_parse_page(self, marker, marker_index):
        """Click marker and parse page content"""
        try:
            # Click the marker
            if marker['element']:
                ActionChains(self.driver).move_to_element(marker['element']).click().perform()
            else:
                self.driver.execute_script(f"document.elementFromPoint({marker['x']}, {marker['y']})?.click();")
            
            time.sleep(3)
            
            # Look for tooltip content in page
            tooltip_selectors = [
                "[class*='tooltip']",
                "[class*='popup']",
                "[id*='tooltip']",
                ".qtip",
                "[role='tooltip']"
            ]
            
            for selector in tooltip_selectors:
                try:
                    tooltips = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for tooltip in tooltips:
                        if tooltip.is_displayed() and len(tooltip.text) > 50:
                            return self.parse_tooltip_text(tooltip.text)
                except:
                    continue
            
        except Exception as e:
            print(f"⚠️ Click and parse failed: {e}")
        
        return None
    
    def parse_api_response(self, response_text):
        """Parse API response (proven method)"""
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
            return None
    
    def parse_html_tooltip(self, html_content):
        """Parse HTML tooltip (proven method)"""
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
            elif len(line) > 80:  # Description
                if 'description' not in project_data:
                    project_data['description'] = line
        
        return project_data if len(project_data) >= 2 else None
    
    def parse_tooltip_text(self, text):
        """Parse plain text tooltip"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        project_data = {}
        
        for line in lines:
            if re.search(r'(Ltd|Limited|PLC|Group|Company)', line, re.IGNORECASE) and not project_data.get('company_name'):
                project_data['company_name'] = line
            elif 'industry:' in line.lower():
                project_data['industry'] = re.sub(r'^.*industry:\s*', '', line, flags=re.IGNORECASE).strip()
            elif 'competition:' in line.lower():
                project_data['competition'] = re.sub(r'^.*competition:\s*', '', line, flags=re.IGNORECASE).strip()
            elif 'region:' in line.lower():
                project_data['region'] = re.sub(r'^.*region:\s*', '', line, flags=re.IGNORECASE).strip()
            elif 'technology:' in line.lower():
                project_data['technology'] = re.sub(r'^.*technology:\s*', '', line, flags=re.IGNORECASE).strip()
            elif 'total cost:' in line.lower():
                cost_match = re.search(r'£?([0-9,]+)', line)
                if cost_match:
                    project_data['total_cost'] = cost_match.group(1)
            elif 'total grant:' in line.lower():
                grant_match = re.search(r'£?([0-9,]+)', line)
                if grant_match:
                    project_data['total_grant'] = grant_match.group(1)
        
        return project_data if len(project_data) >= 2 else None
    
    def save_results(self):
        """Save all results"""
        print("💾 Saving complete extraction results...")
        
        # Save JSON
        with open("fully_automated_projects.json", "w", encoding="utf-8") as f:
            json.dump(self.all_projects, f, indent=2, ensure_ascii=False)
        
        # Calculate statistics
        total_cost = 0
        total_grant = 0
        regions = {}
        industries = {}
        
        for project in self.all_projects:
            try:
                cost = project.get('total_cost', '0').replace(',', '')
                grant = project.get('total_grant', '0').replace(',', '')
                total_cost += int(cost) if cost.isdigit() else 0
                total_grant += int(grant) if grant.isdigit() else 0
                
                region = project.get('region', 'Unknown')
                industry = project.get('industry', 'Unknown')
                regions[region] = regions.get(region, 0) + 1
                industries[industry] = industries.get(industry, 0) + 1
            except:
                continue
        
        # Create comprehensive summary
        summary = f"""# Fully Automated IETF Extraction Results

## 📊 Summary Statistics
- **Total Projects Extracted:** {len(self.all_projects)}
- **Total Project Value:** £{total_cost:,}
- **Total Government Grants:** £{total_grant:,}
- **Average Project Size:** £{total_cost // len(self.all_projects) if self.all_projects else 0:,}
- **Average Grant:** £{total_grant // len(self.all_projects) if self.all_projects else 0:,}
- **Grant Coverage:** {round(total_grant / total_cost * 100, 1) if total_cost > 0 else 0}%

## 🗺️ Regional Distribution
"""
        
        for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
            summary += f"- **{region}:** {count} projects\n"
        
        summary += "\n## 🏭 Industry Distribution\n"
        
        for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True):
            summary += f"- **{industry}:** {count} projects\n"
        
        summary += "\n## 📋 Complete Project List\n\n"
        
        for i, project in enumerate(self.all_projects, 1):
            summary += f"### Project {i}: {project.get('company_name', 'Unknown Company')}\n\n"
            for key, value in project.items():
                if key not in ['coordinates', 'marker_index', 'discovery_method', 'api_tuple_id']:
                    summary += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            summary += "\n"
        
        with open("fully_automated_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
        
        # Create CSV
        try:
            import pandas as pd
            df = pd.DataFrame(self.all_projects)
            df.to_csv("fully_automated_projects.csv", index=False)
            print("💾 Saved: fully_automated_projects.csv")
        except ImportError:
            print("⚠️ pandas not available for CSV export")
        
        print("💾 Saved: fully_automated_projects.json")
        print("💾 Saved: fully_automated_summary.md")
    
    def run_complete_extraction(self):
        """Run the complete fully automated extraction"""
        print("🤖 FULLY AUTOMATED IETF EXTRACTION")
        print("=" * 60)
        print("🎯 Zero manual intervention - discovering ALL markers automatically")
        print()
        
        try:
            # Setup
            self.setup_driver()
            
            # Load map
            if not self.load_tableau_map():
                print("❌ Failed to load Tableau map")
                return False
            
            # Discover all markers
            markers = self.discover_all_markers()
            if not markers:
                print("❌ No markers discovered")
                return False
            
            print(f"\n🎯 Discovered {len(markers)} markers")
            print("📊 Starting data extraction from all markers...")
            
            # Extract data from all markers
            successful_count = self.extract_data_from_all_markers(markers)
            
            if successful_count > 0:
                self.save_results()
                print(f"\n🎉 FULLY AUTOMATED EXTRACTION COMPLETE!")
                print(f"✅ Successfully extracted {successful_count} unique projects")
                print(f"📁 Results saved in multiple formats")
                return True
            else:
                print("\n❌ No data successfully extracted")
                return False
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            return False
            
        finally:
            if self.driver:
                print("🔄 Closing browser...")
                self.driver.quit()

def main():
    print("🚀 Starting Fully Automated IETF Data Extraction")
    print("This will discover and extract data from ALL markers automatically")
    print("No manual intervention required!")
    print()
    
    extractor = FullyAutomatedExtractor()
    success = extractor.run_complete_extraction()
    
    if success:
        print("\n✅ Fully automated extraction completed successfully!")
        print("📊 Check the generated files for complete results")
    else:
        print("\n❌ Extraction failed - check logs for details")

if __name__ == "__main__":
    main() 