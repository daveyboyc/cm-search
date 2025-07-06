#!/usr/bin/env python3
"""
Intelligent Marker Discoverer - Advanced Tableau extraction
Uses Tableau-specific techniques to find ALL markers automatically
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

class IntelligentMarkerDiscoverer:
    def __init__(self):
        self.driver = None
        self.session_id = None
        self.cookies = None
        self.all_projects = []
        self.processed_tuples = set()
        self.worksheet_name = "Map External"
        self.dashboard_name = "Map Dashboard"
        
    def setup_driver(self):
        """Setup Chrome with optimal settings for Tableau"""
        print("🧠 Setting up intelligent Chrome driver for Tableau...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance settings
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")
        chrome_options.add_experimental_option('perfLoggingPrefs', {
            'enableNetwork': True,
            'enablePage': True
        })
        chrome_options.add_experimental_option('loggingPrefs', {
            'performance': 'ALL',
            'browser': 'ALL'
        })
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enable Network domain for monitoring
        self.driver.execute_cdp_cmd('Network.enable', {})
        self.driver.execute_cdp_cmd('Runtime.enable', {})
        
        print("✅ Intelligent driver ready with advanced monitoring")
        
    def load_and_analyze_tableau(self):
        """Load Tableau and perform deep analysis"""
        print("📊 Loading and analyzing Tableau dashboard...")
        
        url = "https://public.tableau.com/views/IETFProjectMap/MapDashboard"
        self.driver.get(url)
        
        # Wait for initial load
        time.sleep(15)
        
        # Extract session information
        self.extract_tableau_metadata()
        
        # Switch to iframe and analyze structure
        iframe_success = self.enter_iframe_context()
        if not iframe_success:
            return False
        
        # Wait for full Tableau rendering
        time.sleep(12)
        
        # Analyze Tableau internal structure
        self.analyze_tableau_structure()
        
        return True
    
    def extract_tableau_metadata(self):
        """Extract Tableau session and metadata"""
        print("🔍 Extracting Tableau metadata...")
        
        # Get cookies
        cookies = self.driver.get_cookies()
        self.cookies = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print(f"✅ Extracted {len(cookies)} cookies")
        
        # Find session ID with multiple patterns
        page_source = self.driver.page_source
        session_patterns = [
            r'sessions/([A-F0-9]{32}-\d+:\d+)',
            r'"sessionId"\s*:\s*"([^"]+)"',
            r'sessionId[=:]([A-F0-9-]+)',
            r'workbook[^}]*session[^}]*?([A-F0-9]{32}-\d+:\d+)'
        ]
        
        for pattern in session_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                self.session_id = matches[0]
                print(f"✅ Session ID found: {self.session_id[:30]}...")
                break
        
        # Extract worksheet and dashboard names
        worksheet_match = re.search(r'"worksheetName"\s*:\s*"([^"]+)"', page_source)
        if worksheet_match:
            self.worksheet_name = worksheet_match.group(1)
            print(f"✅ Worksheet: {self.worksheet_name}")
        
        dashboard_match = re.search(r'"dashboardName"\s*:\s*"([^"]+)"', page_source)
        if dashboard_match:
            self.dashboard_name = dashboard_match.group(1)
            print(f"✅ Dashboard: {self.dashboard_name}")
    
    def enter_iframe_context(self):
        """Enter iframe with retries"""
        print("🔍 Entering Tableau iframe context...")
        
        for attempt in range(3):
            try:
                iframe = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                
                # Wait for iframe to be ready
                WebDriverWait(self.driver, 10).until(
                    lambda d: iframe.size['width'] > 0 and iframe.size['height'] > 0
                )
                
                self.driver.switch_to.frame(iframe)
                print("✅ Successfully entered iframe context")
                return True
                
            except Exception as e:
                print(f"⚠️ Iframe attempt {attempt + 1} failed: {e}")
                time.sleep(5)
        
        return False
    
    def analyze_tableau_structure(self):
        """Analyze Tableau's internal structure"""
        print("🔬 Analyzing Tableau internal structure...")
        
        # Check for Tableau-specific elements
        tableau_indicators = [
            "svg",
            "[class*='tab-']",
            "[data-tb-test-id]", 
            ".tabTableauViz",
            "g[class*='mark']",
            "circle[class*='mark']"
        ]
        
        for indicator in tableau_indicators:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                if elements:
                    print(f"✅ Found {len(elements)} {indicator} elements")
            except:
                continue
        
        # Get page structure
        try:
            page_html = self.driver.page_source
            print(f"📄 Page content length: {len(page_html)} characters")
            
            # Look for data attributes
            if 'data-tb-test-id' in page_html:
                print("✅ Tableau test IDs detected")
            if 'tableau' in page_html.lower():
                print("✅ Tableau references found")
                
        except Exception as e:
            print(f"⚠️ Structure analysis failed: {e}")
    
    def discover_markers_systematically(self):
        """Discover markers using multiple intelligent strategies"""
        print("🎯 Starting systematic marker discovery...")
        
        all_markers = []
        
        # Strategy 1: Tableau-specific SVG discovery
        svg_markers = self.discover_svg_markers()
        all_markers.extend(svg_markers)
        print(f"📍 SVG strategy: {len(svg_markers)} markers")
        
        # Strategy 2: Interactive element discovery
        interactive_markers = self.discover_interactive_elements()
        all_markers.extend(interactive_markers)
        print(f"🖱️ Interactive strategy: {len(interactive_markers)} markers")
        
        # Strategy 3: Network-guided discovery
        network_markers = self.discover_via_network_monitoring()
        all_markers.extend(network_markers)
        print(f"📡 Network strategy: {len(network_markers)} markers")
        
        # Strategy 4: Coordinate-based systematic scan
        if len(all_markers) < 10:  # If we haven't found many markers
            scan_markers = self.systematic_coordinate_scan()
            all_markers.extend(scan_markers)
            print(f"🔍 Scan strategy: {len(scan_markers)} markers")
        
        # Strategy 5: JavaScript-based discovery
        js_markers = self.discover_via_javascript()
        all_markers.extend(js_markers)
        print(f"⚡ JavaScript strategy: {len(js_markers)} markers")
        
        # Deduplicate and validate
        unique_markers = self.validate_and_deduplicate(all_markers)
        print(f"🎯 Total unique valid markers: {len(unique_markers)}")
        
        return unique_markers
    
    def discover_svg_markers(self):
        """Discover SVG-based markers (most common in Tableau)"""
        markers = []
        
        svg_selectors = [
            "svg circle[r]",
            "g[class*='mark'] circle",
            "circle[class*='mark']",
            "svg g circle",
            ".mark circle",
            "path[d][class*='mark']",
            "circle[data-tb-test-id]",
            "g[data-tb-test-id] circle"
        ]
        
        for selector in svg_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if self.is_valid_marker_element(element):
                        location = element.location_once_scrolled_into_view
                        size = element.size
                        
                        markers.append({
                            'x': location['x'] + size['width'] // 2,
                            'y': location['y'] + size['height'] // 2,
                            'element': element,
                            'type': 'svg',
                            'selector': selector,
                            'size': size
                        })
                
                if markers:
                    print(f"✅ SVG selector '{selector}' found {len(markers)} markers")
                    break
                    
            except Exception as e:
                continue
        
        return markers
    
    def discover_interactive_elements(self):
        """Discover interactive elements that could be markers"""
        markers = []
        
        # Look for clickable elements with specific attributes
        interactive_selectors = [
            "[onclick]",
            "[data-click]",
            "[role='button']",
            ".clickable",
            "[cursor='pointer']",
            "[style*='cursor: pointer']"
        ]
        
        for selector in interactive_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if self.is_valid_marker_element(element) and element.is_displayed():
                        location = element.location_once_scrolled_into_view
                        size = element.size
                        
                        markers.append({
                            'x': location['x'] + size['width'] // 2,
                            'y': location['y'] + size['height'] // 2,
                            'element': element,
                            'type': 'interactive',
                            'selector': selector,
                            'size': size
                        })
                        
            except Exception as e:
                continue
        
        return markers
    
    def discover_via_network_monitoring(self):
        """Discover markers by monitoring network requests during scanning"""
        print("📡 Network-guided marker discovery...")
        
        markers = []
        
        # Clear network logs
        try:
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        except:
            pass
        
        # Perform strategic clicking while monitoring
        test_coordinates = [
            (300, 300), (500, 350), (700, 400), (400, 500),
            (600, 300), (350, 450), (750, 350), (450, 400),
            (800, 500), (250, 400), (550, 500), (650, 350),
            (400, 600), (500, 250), (350, 350), (750, 450)
        ]
        
        for x, y in test_coordinates:
            try:
                # Click and monitor
                self.driver.execute_script(f"""
                    var element = document.elementFromPoint({x}, {y});
                    if (element) {{
                        element.click();
                    }}
                """)
                
                time.sleep(1.5)
                
                # Check for tooltip request
                if self.check_network_for_tooltip():
                    markers.append({
                        'x': x,
                        'y': y,
                        'element': None,
                        'type': 'network',
                        'selector': 'network_detected',
                        'size': {'width': 10, 'height': 10}
                    })
                    print(f"📡 Network activity at ({x}, {y})")
                
            except Exception as e:
                continue
        
        return markers
    
    def systematic_coordinate_scan(self):
        """Systematic coordinate scanning for markers"""
        print("🔍 Performing systematic coordinate scan...")
        
        markers = []
        
        # Get viewport dimensions
        viewport = self.driver.execute_script("return {width: window.innerWidth, height: window.innerHeight};")
        
        # Scan in a grid pattern with optimized spacing
        step_x = max(40, viewport['width'] // 30)
        step_y = max(40, viewport['height'] // 20)
        
        for y in range(100, viewport['height'] - 100, step_y):
            for x in range(100, viewport['width'] - 100, step_x):
                try:
                    # Get element at position
                    element_info = self.driver.execute_script(f"""
                        var element = document.elementFromPoint({x}, {y});
                        if (!element) return null;
                        
                        var rect = element.getBoundingClientRect();
                        var style = window.getComputedStyle(element);
                        
                        return {{
                            tagName: element.tagName,
                            className: element.className,
                            cursor: style.cursor,
                            width: rect.width,
                            height: rect.height,
                            hasClick: element.onclick !== null,
                            isVisible: rect.width > 0 && rect.height > 0
                        }};
                    """)
                    
                    if element_info and self.is_likely_marker_by_info(element_info):
                        markers.append({
                            'x': x,
                            'y': y,
                            'element': None,
                            'type': 'scan',
                            'selector': 'coordinate_scan',
                            'size': {'width': element_info['width'], 'height': element_info['height']}
                        })
                
                except Exception as e:
                    continue
        
        print(f"🔍 Coordinate scan found {len(markers)} potential markers")
        return markers
    
    def discover_via_javascript(self):
        """Use JavaScript to discover markers in the DOM"""
        print("⚡ JavaScript-based marker discovery...")
        
        try:
            # Advanced JavaScript to find potential markers
            marker_data = self.driver.execute_script("""
                var markers = [];
                
                // Find SVG circles
                var circles = document.querySelectorAll('circle');
                circles.forEach(function(circle, index) {
                    var rect = circle.getBoundingClientRect();
                    if (rect.width > 3 && rect.width < 100 && rect.height > 3 && rect.height < 100) {
                        var centerX = rect.left + rect.width / 2;
                        var centerY = rect.top + rect.height / 2;
                        
                        markers.push({
                            x: centerX,
                            y: centerY,
                            type: 'js_circle',
                            index: index,
                            radius: circle.getAttribute('r'),
                            class: circle.className.baseVal || circle.className
                        });
                    }
                });
                
                // Find elements with 'mark' in class name
                var markElements = document.querySelectorAll('[class*="mark"]');
                markElements.forEach(function(element, index) {
                    var rect = element.getBoundingClientRect();
                    if (rect.width > 3 && rect.width < 100 && rect.height > 3 && rect.height < 100) {
                        var centerX = rect.left + rect.width / 2;
                        var centerY = rect.top + rect.height / 2;
                        
                        markers.push({
                            x: centerX,
                            y: centerY,
                            type: 'js_mark',
                            index: index,
                            tagName: element.tagName,
                            class: element.className
                        });
                    }
                });
                
                return markers;
            """)
            
            # Convert JavaScript results to marker format
            markers = []
            for js_marker in marker_data:
                markers.append({
                    'x': int(js_marker['x']),
                    'y': int(js_marker['y']),
                    'element': None,
                    'type': js_marker['type'],
                    'selector': 'javascript_discovery',
                    'size': {'width': 10, 'height': 10}
                })
            
            print(f"⚡ JavaScript discovery found {len(markers)} markers")
            return markers
            
        except Exception as e:
            print(f"⚠️ JavaScript discovery failed: {e}")
            return []
    
    def is_valid_marker_element(self, element):
        """Check if element is a valid marker"""
        try:
            if not element.is_displayed():
                return False
            
            size = element.size
            if size['width'] < 3 or size['height'] < 3:
                return False
            
            if size['width'] > 200 or size['height'] > 200:
                return False
            
            # Check for marker-like attributes
            tag_name = element.tag_name.lower()
            if tag_name in ['circle', 'ellipse', 'rect', 'path']:
                return True
            
            class_name = (element.get_attribute('class') or '').lower()
            if any(keyword in class_name for keyword in ['mark', 'marker', 'dot', 'point']):
                return True
            
            return False
            
        except Exception as e:
            return False
    
    def is_likely_marker_by_info(self, element_info):
        """Check if element info suggests a marker"""
        if not element_info['isVisible']:
            return False
        
        # Size check
        if (element_info['width'] < 5 or element_info['height'] < 5 or
            element_info['width'] > 100 or element_info['height'] > 100):
            return False
        
        # Tag and class checks
        tag_name = element_info['tagName'].lower()
        class_name = element_info['className'].lower()
        
        if tag_name in ['circle', 'ellipse', 'rect', 'path']:
            return True
        
        if any(keyword in class_name for keyword in ['mark', 'marker', 'dot', 'point']):
            return True
        
        # Cursor check
        if element_info['cursor'] == 'pointer':
            return True
        
        return False
    
    def check_network_for_tooltip(self):
        """Check if tooltip request was made"""
        try:
            logs = self.driver.get_log('performance')
            for log in logs[-3:]:  # Check recent logs
                message = json.loads(log['message'])
                if (message.get('message', {}).get('method') == 'Network.responseReceived'):
                    url = message['message']['params']['response'].get('url', '')
                    if 'render-tooltip-server' in url:
                        return True
            return False
        except Exception as e:
            return False
    
    def validate_and_deduplicate(self, markers):
        """Validate and remove duplicate markers"""
        if not markers:
            return []
        
        valid_markers = []
        min_distance = 25  # Minimum pixels between markers
        
        for marker in markers:
            # Basic validation
            if marker['x'] < 50 or marker['y'] < 50:
                continue
            
            # Check for duplicates
            is_duplicate = False
            for existing in valid_markers:
                distance = ((marker['x'] - existing['x'])**2 + (marker['y'] - existing['y'])**2)**0.5
                if distance < min_distance:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                valid_markers.append(marker)
        
        return valid_markers
    
    def extract_all_marker_data(self, markers):
        """Extract data from all discovered markers"""
        print(f"🚀 Extracting data from {len(markers)} markers...")
        
        successful_extractions = 0
        
        for i, marker in enumerate(markers):
            print(f"\n🎯 Processing marker {i+1}/{len(markers)} at ({marker['x']}, {marker['y']})...")
            
            project_data = None
            
            # Try direct API extraction first (most reliable)
            if self.session_id:
                project_data = self.extract_via_direct_api(marker, i+1)
            
            # Try click-based extraction if API fails
            if not project_data:
                project_data = self.extract_via_click(marker, i+1)
            
            if project_data:
                # Add metadata
                project_data['marker_index'] = i + 1
                project_data['coordinates'] = {'x': marker['x'], 'y': marker['y']}
                project_data['discovery_method'] = marker['type']
                project_data['discovery_selector'] = marker['selector']
                
                # Check for duplicates
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
            
            # Rate limiting
            time.sleep(1.5)
        
        print(f"\n🎉 EXTRACTION COMPLETE: {successful_extractions} unique projects found!")
        return successful_extractions
    
    def extract_via_direct_api(self, marker, marker_index):
        """Extract data using direct API call"""
        try:
            if not self.session_id:
                return None
            
            url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{self.session_id}/commands/tabsrv/render-tooltip-server"
            
            headers = {
                'accept': 'text/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': f'multipart/form-data; boundary=intelligent{marker_index}',
                'cookie': self.cookies,
                'origin': 'https://public.tableau.com',
                'referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            boundary = f"intelligent{marker_index}"
            data = self.build_api_request_data(boundary, marker, marker_index)
            
            response = requests.post(url, headers=headers, data=data, timeout=15)
            
            if response.status_code == 200 and len(response.text) > 1000:
                return self.parse_api_response(response.text)
            
        except Exception as e:
            print(f"⚠️ API extraction failed: {e}")
        
        return None
    
    def build_api_request_data(self, boundary, marker, marker_index):
        """Build the multipart form data for API request"""
        return f'''--{boundary}\r
Content-Disposition: form-data; name="worksheet"\r
\r
{self.worksheet_name}\r
--{boundary}\r
Content-Disposition: form-data; name="dashboard"\r
\r
{self.dashboard_name}\r
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
intelligent{marker_index}extract\r
--{boundary}--\r
'''
    
    def extract_via_click(self, marker, marker_index):
        """Extract data by clicking marker"""
        try:
            # Click the marker
            if marker['element']:
                ActionChains(self.driver).move_to_element(marker['element']).click().perform()
            else:
                self.driver.execute_script(f"document.elementFromPoint({marker['x']}, {marker['y']})?.click();")
            
            time.sleep(3)
            
            # Look for tooltip or popup content
            tooltip_content = self.find_tooltip_content()
            if tooltip_content:
                return self.parse_tooltip_content(tooltip_content)
            
        except Exception as e:
            print(f"⚠️ Click extraction failed: {e}")
        
        return None
    
    def find_tooltip_content(self):
        """Find tooltip content in various forms"""
        tooltip_selectors = [
            "[class*='tooltip']",
            "[class*='popup']", 
            "[id*='tooltip']",
            ".qtip",
            "[role='tooltip']",
            "[data-tb-test-id*='tooltip']"
        ]
        
        for selector in tooltip_selectors:
            try:
                tooltips = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for tooltip in tooltips:
                    if tooltip.is_displayed() and len(tooltip.text) > 50:
                        return tooltip.text
            except:
                continue
        
        return None
    
    def parse_api_response(self, response_text):
        """Parse API response to extract project data"""
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
        """Parse HTML tooltip to extract structured data"""
        # Clean up HTML
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
        
        return project_data if len(project_data) >= 2 else None
    
    def parse_tooltip_content(self, text):
        """Parse plain text tooltip content"""
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
    
    def save_comprehensive_results(self):
        """Save comprehensive results with analysis"""
        print("💾 Saving comprehensive extraction results...")
        
        # Save raw JSON
        with open("intelligent_extraction.json", "w", encoding="utf-8") as f:
            json.dump(self.all_projects, f, indent=2, ensure_ascii=False)
        
        # Generate comprehensive analysis
        analysis = self.generate_comprehensive_analysis()
        
        with open("intelligent_extraction_analysis.md", "w", encoding="utf-8") as f:
            f.write(analysis)
        
        # Save CSV if possible
        try:
            import pandas as pd
            df = pd.DataFrame(self.all_projects)
            df.to_csv("intelligent_extraction.csv", index=False)
            print("💾 Saved CSV format")
        except ImportError:
            print("⚠️ pandas not available for CSV")
        
        print("💾 Results saved successfully")
    
    def generate_comprehensive_analysis(self):
        """Generate comprehensive analysis of extracted data"""
        total_projects = len(self.all_projects)
        total_cost = sum(int(p.get('total_cost', '0').replace(',', '')) for p in self.all_projects if p.get('total_cost', '').replace(',', '').isdigit())
        total_grant = sum(int(p.get('total_grant', '0').replace(',', '')) for p in self.all_projects if p.get('total_grant', '').replace(',', '').isdigit())
        
        # Regional analysis
        regions = {}
        industries = {}
        technologies = {}
        
        for project in self.all_projects:
            region = project.get('region', 'Unknown')
            industry = project.get('industry', 'Unknown')
            technology = project.get('technology', 'Unknown')
            
            regions[region] = regions.get(region, 0) + 1
            industries[industry] = industries.get(industry, 0) + 1
            technologies[technology] = technologies.get(technology, 0) + 1
        
        analysis = f"""# Intelligent IETF Extraction - Comprehensive Analysis

## 🎯 Extraction Summary
- **Total Projects Discovered:** {total_projects}
- **Total Investment Value:** £{total_cost:,}
- **Total Government Grants:** £{total_grant:,}
- **Average Project Value:** £{total_cost // total_projects if total_projects > 0 else 0:,}
- **Average Grant Amount:** £{total_grant // total_projects if total_projects > 0 else 0:,}
- **Government Grant Coverage:** {round(total_grant / total_cost * 100, 1) if total_cost > 0 else 0}%

## 🗺️ Regional Distribution
"""
        
        for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1)
            analysis += f"- **{region}:** {count} projects ({percentage}%)\n"
        
        analysis += "\n## 🏭 Industry Breakdown\n"
        
        for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1)
            analysis += f"- **{industry}:** {count} projects ({percentage}%)\n"
        
        analysis += "\n## 🔬 Technology Focus\n"
        
        for technology, count in sorted(technologies.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1)
            analysis += f"- **{technology}:** {count} projects ({percentage}%)\n"
        
        analysis += "\n## 📊 Discovery Method Analysis\n"
        
        methods = {}
        for project in self.all_projects:
            method = project.get('discovery_method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        
        for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
            analysis += f"- **{method.title()}:** {count} projects\n"
        
        analysis += "\n## 📋 Complete Project Database\n\n"
        
        for i, project in enumerate(self.all_projects, 1):
            analysis += f"### {i}. {project.get('company_name', 'Unknown Company')}\n\n"
            
            fields = [
                ('Industry', 'industry'),
                ('Competition', 'competition'),
                ('Region', 'region'),
                ('Project Type', 'project_type'),
                ('Technology', 'technology'),
                ('Solution', 'solution'),
                ('Total Cost', 'total_cost'),
                ('Total Grant', 'total_grant'),
                ('Government URL', 'government_url'),
                ('Description', 'description')
            ]
            
            for label, key in fields:
                value = project.get(key)
                if value:
                    if key == 'government_url':
                        analysis += f"- **{label}:** [{value}]({value})\n"
                    elif key in ['total_cost', 'total_grant']:
                        analysis += f"- **{label}:** £{value}\n"
                    else:
                        analysis += f"- **{label}:** {value}\n"
            
            analysis += f"- **Discovery Method:** {project.get('discovery_method', 'unknown')}\n"
            analysis += f"- **Coordinates:** ({project.get('coordinates', {}).get('x', 'N/A')}, {project.get('coordinates', {}).get('y', 'N/A')})\n\n"
        
        return analysis
    
    def run_intelligent_extraction(self):
        """Run the complete intelligent extraction process"""
        print("🧠 INTELLIGENT IETF MARKER DISCOVERY & EXTRACTION")
        print("=" * 70)
        print("🎯 Using advanced Tableau-specific techniques")
        print()
        
        try:
            # Setup
            self.setup_driver()
            
            # Load and analyze
            if not self.load_and_analyze_tableau():
                print("❌ Failed to load and analyze Tableau dashboard")
                return False
            
            # Discover markers
            markers = self.discover_markers_systematically()
            if not markers:
                print("❌ No markers discovered with intelligent methods")
                return False
            
            print(f"\n🎯 DISCOVERED {len(markers)} UNIQUE MARKERS")
            print("🚀 Beginning intelligent data extraction...")
            
            # Extract data
            successful_count = self.extract_all_marker_data(markers)
            
            if successful_count > 0:
                self.save_comprehensive_results()
                print(f"\n🎉 INTELLIGENT EXTRACTION COMPLETE!")
                print(f"✅ Successfully extracted {successful_count} unique projects")
                print(f"📊 Comprehensive analysis generated")
                print(f"📁 Results available in multiple formats")
                return True
            else:
                print("\n❌ No projects successfully extracted")
                return False
            
        except Exception as e:
            print(f"❌ Fatal error during intelligent extraction: {e}")
            return False
            
        finally:
            if self.driver:
                print("🔄 Cleaning up...")
                self.driver.quit()

def main():
    print("🚀 INTELLIGENT IETF EXTRACTION SYSTEM")
    print("Using advanced Tableau-specific discovery techniques")
    print("This will systematically find and extract ALL marker data")
    print()
    
    discoverer = IntelligentMarkerDiscoverer()
    success = discoverer.run_intelligent_extraction()
    
    if success:
        print("\n✅ Intelligent extraction completed successfully!")
        print("📊 Check generated files for comprehensive results")
    else:
        print("\n❌ Intelligent extraction failed")

if __name__ == "__main__":
    main() 