#!/usr/bin/env python3
"""
Manual Session IETF Extractor - Uses fresh session from browser
This is the practical solution that works with manually captured sessions
"""
import json
import time
import re
import requests
import html
from urllib.parse import unquote

class ManualSessionExtractor:
    def __init__(self, session_id, cookies_string=None):
        self.session_id = session_id
        self.cookies = cookies_string or "AWSELBCORS=1234567890ABCDEF; _ga=GA1.1.123456789.1234567890"
        self.all_projects = []
        self.processed_tuples = set()
        
    def extract_all_markers(self, max_markers=200):
        """Systematically extract data from all possible marker positions"""
        print(f"🚀 SYSTEMATIC MARKER EXTRACTION")
        print(f"Session: {self.session_id[:30]}...")
        print(f"Testing up to {max_markers} marker positions")
        print("=" * 60)
        
        successful_extractions = 0
        
        # Strategy 1: Sequential tuple IDs (most reliable)
        print("🎯 Strategy 1: Testing sequential tuple IDs...")
        for tuple_id in range(1, 151):  # Test first 150 tuple IDs
            print(f"Testing tuple ID {tuple_id}...", end=" ")
            
            project_data = self.extract_via_api(tuple_id, 500, 400)  # Use center coordinates
            
            if project_data:
                if tuple_id not in self.processed_tuples:
                    project_data['extraction_method'] = 'sequential_tuple'
                    project_data['tuple_id'] = tuple_id
                    self.all_projects.append(project_data)
                    self.processed_tuples.add(tuple_id)
                    successful_extractions += 1
                    
                    company = project_data.get('company_name', 'Unknown')
                    cost = project_data.get('total_cost', 'N/A')
                    print(f"✅ SUCCESS #{successful_extractions}: {company} - £{cost}")
                else:
                    print("⚠️ Duplicate")
            else:
                print("❌")
            
            time.sleep(1)  # Rate limiting
        
        # Strategy 2: Grid-based coordinate testing
        print(f"\n🎯 Strategy 2: Grid-based coordinate testing...")
        grid_points = []
        
        # Create a grid of coordinates across UK map area
        for x in range(200, 801, 50):  # X: 200 to 800, step 50
            for y in range(150, 601, 50):  # Y: 150 to 600, step 50
                grid_points.append((x, y))
        
        print(f"Testing {len(grid_points)} grid coordinates...")
        
        for i, (x, y) in enumerate(grid_points):
            if i % 20 == 0:  # Progress update every 20 tests
                print(f"Progress: {i}/{len(grid_points)} coordinates tested")
            
            project_data = self.extract_via_api(i + 200, x, y)  # Use high tuple IDs to avoid conflicts
            
            if project_data:
                # Check if this is actually new data (not just different coordinates for same project)
                is_new = True
                for existing in self.all_projects:
                    if (existing.get('company_name') == project_data.get('company_name') and
                        existing.get('total_cost') == project_data.get('total_cost')):
                        is_new = False
                        break
                
                if is_new:
                    project_data['extraction_method'] = 'grid_coordinate'
                    project_data['coordinates'] = {'x': x, 'y': y}
                    self.all_projects.append(project_data)
                    successful_extractions += 1
                    
                    company = project_data.get('company_name', 'Unknown')
                    print(f"✅ GRID SUCCESS #{successful_extractions}: {company} at ({x},{y})")
            
            time.sleep(0.8)  # Slightly faster rate limiting
        
        # Strategy 3: Known working coordinates (from successful manual extractions)
        print(f"\n🎯 Strategy 3: Testing known working coordinate patterns...")
        known_patterns = [
            # Based on previous successful extractions - these coordinate patterns often work
            (469, 591), (450, 580), (480, 600), (460, 570), (490, 610),
            (400, 550), (500, 630), (430, 560), (470, 620), (440, 590),
            (520, 580), (380, 570), (510, 600), (420, 610), (490, 570),
            (350, 580), (530, 590), (410, 600), (480, 640), (460, 550)
        ]
        
        for i, (x, y) in enumerate(known_patterns):
            project_data = self.extract_via_api(i + 300, x, y)  # Use even higher tuple IDs
            
            if project_data:
                # Check uniqueness
                is_new = True
                for existing in self.all_projects:
                    if (existing.get('company_name') == project_data.get('company_name') and
                        existing.get('total_cost') == project_data.get('total_cost')):
                        is_new = False
                        break
                
                if is_new:
                    project_data['extraction_method'] = 'known_pattern'
                    project_data['coordinates'] = {'x': x, 'y': y}
                    self.all_projects.append(project_data)
                    successful_extractions += 1
                    
                    company = project_data.get('company_name', 'Unknown')
                    print(f"✅ PATTERN SUCCESS #{successful_extractions}: {company}")
            
            time.sleep(1)
        
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"✅ Successfully extracted {successful_extractions} unique projects")
        print(f"📊 Using {len(set(p.get('extraction_method') for p in self.all_projects))} different extraction methods")
        
        return successful_extractions
    
    def extract_via_api(self, tuple_id, x, y):
        """Extract data using the proven Tableau API method"""
        try:
            url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{self.session_id}/commands/tabsrv/render-tooltip-server"
            
            headers = {
                'accept': 'text/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': f'multipart/form-data; boundary=extract{tuple_id}',
                'cookie': self.cookies,
                'origin': 'https://public.tableau.com',
                'referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            boundary = f"extract{tuple_id}"
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
[{tuple_id}]\r
--{boundary}\r
Content-Disposition: form-data; name="vizRegionRect"\r
\r
{{"r":"viz","x":{x},"y":{y},"w":0,"h":0,"fieldVector":null}}\r
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
extract{tuple_id}manual\r
--{boundary}--\r
"""
            
            response = requests.post(url, headers=headers, data=data, timeout=15)
            
            if response.status_code == 200 and len(response.text) > 1000:
                return self.parse_tableau_response(response.text)
            elif response.status_code == 410:
                print(f"⚠️ Session expired! Please get a fresh session ID.")
                return None
            else:
                return None
            
        except Exception as e:
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
    
    def save_results(self):
        """Save comprehensive results"""
        print("💾 Saving extraction results...")
        
        # Save JSON
        with open("manual_session_extraction.json", "w", encoding="utf-8") as f:
            json.dump(self.all_projects, f, indent=2, ensure_ascii=False)
        
        # Generate detailed report
        total_projects = len(self.all_projects)
        total_cost = sum(int(p.get('total_cost', '0').replace(',', '')) for p in self.all_projects if p.get('total_cost', '').replace(',', '').isdigit())
        total_grant = sum(int(p.get('total_grant', '0').replace(',', '')) for p in self.all_projects if p.get('total_grant', '').replace(',', '').isdigit())
        
        # Analyze extraction methods
        methods = {}
        regions = {}
        
        for project in self.all_projects:
            method = project.get('extraction_method', 'unknown')
            region = project.get('region', 'Unknown')
            methods[method] = methods.get(method, 0) + 1
            regions[region] = regions.get(region, 0) + 1
        
        report = f"""# Manual Session IETF Extraction Report

## 🎯 Extraction Summary
- **Session ID:** {self.session_id[:30]}...
- **Total Projects Extracted:** {total_projects}
- **Total Investment Value:** £{total_cost:,}
- **Total Government Grants:** £{total_grant:,}
- **Average Project Value:** £{total_cost // total_projects if total_projects > 0 else 0:,}
- **Grant Coverage:** {round(total_grant / total_cost * 100, 1) if total_cost > 0 else 0}%

## 📊 Extraction Method Success
"""
        
        for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1) if total_projects > 0 else 0
            report += f"- **{method.replace('_', ' ').title()}:** {count} projects ({percentage}%)\n"
        
        report += "\n## 🗺️ Regional Distribution\n"
        
        for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1) if total_projects > 0 else 0
            report += f"- **{region}:** {count} projects ({percentage}%)\n"
        
        report += "\n## 📋 Complete Project Database\n\n"
        
        for i, project in enumerate(self.all_projects, 1):
            company = project.get('company_name', 'Unknown Company')
            cost = project.get('total_cost', 'N/A')
            grant = project.get('total_grant', 'N/A')
            region = project.get('region', 'Unknown')
            method = project.get('extraction_method', 'unknown')
            
            report += f"### {i}. {company}\n"
            report += f"- **Total Cost:** £{cost}\n"
            report += f"- **Grant:** £{grant}\n"
            report += f"- **Region:** {region}\n"
            report += f"- **Extraction Method:** {method}\n"
            
            if project.get('industry'):
                report += f"- **Industry:** {project['industry']}\n"
            if project.get('technology'):
                report += f"- **Technology:** {project['technology']}\n"
            if project.get('government_url'):
                report += f"- **Government URL:** [{project['government_url']}]({project['government_url']})\n"
            
            coords = project.get('coordinates', {})
            if coords:
                report += f"- **Coordinates:** ({coords.get('x', 'N/A')}, {coords.get('y', 'N/A')})\n"
            
            report += "\n"
        
        # Save report
        with open("manual_session_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"💾 Results saved:")
        print(f"  📄 manual_session_extraction.json ({total_projects} projects)")
        print(f"  📄 manual_session_report.md (detailed analysis)")

def get_session_from_user():
    """Get fresh session ID from user"""
    print("🔑 SESSION ID REQUIRED")
    print("=" * 50)
    print("To extract all markers, you need a fresh Tableau session ID.")
    print()
    print("📋 How to get it:")
    print("1. Open: https://public.tableau.com/views/IETFProjectMap/MapDashboard")
    print("2. Click on ANY marker to see tooltip")
    print("3. Open browser Developer Tools (F12)")
    print("4. Go to Network tab")
    print("5. Click another marker")
    print("6. Find 'render-tooltip-server' request")
    print("7. Right-click → Copy → Copy as cURL")
    print("8. Paste the cURL command here")
    print()
    
    curl_command = input("Paste your cURL command: ").strip()
    
    # Extract session ID from cURL command
    session_match = re.search(r'sessions/([A-F0-9]{32}-\d+:\d+)', curl_command)
    if session_match:
        session_id = session_match.group(1)
        print(f"✅ Extracted session: {session_id[:30]}...")
        
        # Extract cookies
        cookie_match = re.search(r"'cookie: ([^']+)'", curl_command)
        cookies = cookie_match.group(1) if cookie_match else None
        
        return session_id, cookies
    else:
        print("❌ Could not extract session ID from cURL command")
        return None, None

def main():
    print("🏆 MANUAL SESSION IETF EXTRACTOR")
    print("The practical solution that works with fresh browser sessions")
    print()
    
    # Option 1: Use the known working session (if still valid)
    print("Choose extraction method:")
    print("1. Use fresh session from browser (RECOMMENDED)")
    print("2. Try with previous working session (may be expired)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        session_id, cookies = get_session_from_user()
        if not session_id:
            print("❌ Failed to get valid session")
            return
    else:
        # Use the session that worked before (F4AC68CAE4BC4D3F9CB785AF26BDDB0C-0:0)
        session_id = "F4AC68CAE4BC4D3F9CB785AF26BDDB0C-0:0"
        cookies = None
        print(f"⚠️ Using previous session: {session_id[:30]}... (may be expired)")
    
    # Run extraction
    extractor = ManualSessionExtractor(session_id, cookies)
    success_count = extractor.extract_all_markers()
    extractor.save_results()
    
    if success_count > 0:
        print(f"\n🏆 EXTRACTION SUCCESS!")
        print(f"✅ Successfully extracted {success_count} unique IETF projects")
        print(f"📊 Complete analysis saved to files")
        print(f"💡 This approach can extract from ALL markers automatically")
    else:
        print(f"\n⚠️ No projects extracted")
        print(f"💡 The session may have expired - try getting a fresh one")

if __name__ == "__main__":
    main() 