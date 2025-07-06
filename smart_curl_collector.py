#!/usr/bin/env python3
"""
Smart cURL Collector - Efficient multi-marker data extraction
Makes it easy to collect cURL commands from multiple markers and process them all
"""
import json
import re
import requests
import html
from urllib.parse import unquote
import time

class SmartCurlCollector:
    def __init__(self):
        self.collected_curls = []
        self.processed_projects = []
        
    def interactive_collection_mode(self):
        """Interactive mode to collect multiple cURL commands"""
        print("🎯 Smart cURL Collection Mode")
        print("=" * 50)
        print("This tool makes collecting multiple marker data MUCH easier!")
        print()
        print("📋 INSTRUCTIONS:")
        print("1. Open the IETF Tableau map in your browser")
        print("2. Open DevTools → Network tab → Clear logs")
        print("3. Click a marker → Look for 'render-tooltip-server' request")
        print("4. Right-click → Copy → Copy as cURL")
        print("5. Paste the cURL command here")
        print("6. Repeat for as many markers as you want")
        print("7. Type 'done' when finished")
        print()
        print("💡 TIP: You can collect 10-20 markers quickly this way!")
        print()
        
        curl_count = 0
        
        while True:
            print(f"\n📎 Paste cURL command #{curl_count + 1} (or 'done' to finish):")
            user_input = input().strip()
            
            if user_input.lower() in ['done', 'finish', 'exit', 'stop']:
                break
                
            if user_input.startswith('curl '):
                # Parse and validate the cURL command
                parsed_curl = self.parse_curl_command(user_input, curl_count + 1)
                if parsed_curl:
                    self.collected_curls.append(parsed_curl)
                    curl_count += 1
                    print(f"✅ cURL #{curl_count} collected successfully!")
                    
                    # Show quick preview
                    coords = parsed_curl.get('coordinates', {})
                    session = parsed_curl.get('session_id', 'Unknown')[:20]
                    print(f"   📍 Coordinates: ({coords.get('x', '?')}, {coords.get('y', '?')})")
                    print(f"   🔑 Session: {session}...")
                else:
                    print("❌ Invalid cURL command, please try again")
            else:
                print("❌ Please paste a valid cURL command starting with 'curl '")
        
        print(f"\n📊 Collection complete! {len(self.collected_curls)} cURL commands collected")
        
        if self.collected_curls:
            self.process_all_curls()
        else:
            print("❌ No cURL commands collected")
    
    def batch_mode(self, curl_file="curl_commands.txt"):
        """Batch mode - process cURL commands from a file"""
        print(f"📁 Batch Mode - Reading from {curl_file}")
        print("=" * 50)
        
        try:
            with open(curl_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by curl commands
            curl_commands = re.findall(r'curl [^\\n]*(?:\\\\\\n[^\\n]*)*', content, re.MULTILINE)
            
            print(f"📋 Found {len(curl_commands)} cURL commands in file")
            
            for i, curl_cmd in enumerate(curl_commands):
                parsed_curl = self.parse_curl_command(curl_cmd, i + 1)
                if parsed_curl:
                    self.collected_curls.append(parsed_curl)
            
            if self.collected_curls:
                self.process_all_curls()
            else:
                print("❌ No valid cURL commands found")
                
        except FileNotFoundError:
            print(f"❌ File {curl_file} not found")
            print("💡 Create the file and paste your cURL commands there, one per line")
    
    def parse_curl_command(self, curl_cmd, index):
        """Parse a cURL command and extract key information"""
        try:
            # Extract URL
            url_match = re.search(r"curl '([^']+)'", curl_cmd)
            if not url_match:
                print(f"⚠️ Could not extract URL from cURL #{index}")
                return None
            
            url = url_match.group(1)
            
            # Extract session ID from URL
            session_match = re.search(r'sessions/([A-F0-9-]+)', url)
            if not session_match:
                print(f"⚠️ Could not extract session ID from cURL #{index}")
                return None
            
            session_id = session_match.group(1)
            
            # Extract cookies
            cookie_match = re.search(r"-b '([^']+)'", curl_cmd)
            if not cookie_match:
                cookie_match = re.search(r'--cookie "([^"]+)"', curl_cmd)
            
            cookies = cookie_match.group(1) if cookie_match else ""
            
            # Extract boundary from content-type
            boundary_match = re.search(r'boundary=([^\\s\']+)', curl_cmd)
            boundary = boundary_match.group(1) if boundary_match else f"auto{index}"
            
            # Extract coordinates from data
            coord_match = re.search(r'"x":(\d+),"y":(\d+)', curl_cmd)
            coordinates = {}
            if coord_match:
                coordinates = {
                    'x': int(coord_match.group(1)),
                    'y': int(coord_match.group(2))
                }
            
            # Extract tuple ID
            tuple_match = re.search(r'\\[(\d+)\\]', curl_cmd)
            tuple_id = int(tuple_match.group(1)) if tuple_match else index
            
            return {
                'index': index,
                'url': url,
                'session_id': session_id,
                'cookies': cookies,
                'boundary': boundary,
                'coordinates': coordinates,
                'tuple_id': tuple_id,
                'original_curl': curl_cmd
            }
            
        except Exception as e:
            print(f"⚠️ Error parsing cURL #{index}: {e}")
            return None
    
    def process_all_curls(self):
        """Process all collected cURL commands"""
        print(f"\n🚀 Processing {len(self.collected_curls)} collected requests...")
        print("=" * 60)
        
        successful_extractions = 0
        
        for curl_data in self.collected_curls:
            print(f"\n📡 Processing request #{curl_data['index']}...")
            
            project_data = self.extract_project_data(curl_data)
            if project_data:
                project_data['source_coordinates'] = curl_data['coordinates']
                project_data['source_tuple_id'] = curl_data['tuple_id']
                project_data['extraction_index'] = curl_data['index']
                
                self.processed_projects.append(project_data)
                successful_extractions += 1
                
                company = project_data.get('company_name', 'Unknown Company')
                cost = project_data.get('total_cost', 'N/A')
                print(f"✅ Success {successful_extractions}: {company} - £{cost}")
            else:
                print(f"❌ Failed to extract data from request #{curl_data['index']}")
            
            # Brief delay between requests
            time.sleep(0.5)
        
        print(f"\n🎉 PROCESSING COMPLETE!")
        print(f"📊 Successfully extracted {successful_extractions} out of {len(self.collected_curls)} projects")
        
        if self.processed_projects:
            self.save_all_results()
        
        return successful_extractions
    
    def extract_project_data(self, curl_data):
        """Extract project data using the proven API method"""
        try:
            headers = {
                'accept': 'text/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': f'multipart/form-data; boundary={curl_data["boundary"]}',
                'cookie': curl_data['cookies'],
                'origin': 'https://public.tableau.com',
                'referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
            }
            
            # Rebuild the form data with extracted values
            coords = curl_data['coordinates']
            boundary = curl_data['boundary']
            tuple_id = curl_data['tuple_id']
            
            data = f'--{boundary}\\r\\nContent-Disposition: form-data; name="worksheet"\\r\\n\\r\\nMap External\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="dashboard"\\r\\n\\r\\nMap Dashboard\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="tupleIds"\\r\\n\\r\\n[{tuple_id}]\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="vizRegionRect"\\r\\n\\r\\n{{"r":"viz","x":{coords.get("x", 0)},"y":{coords.get("y", 0)},"w":0,"h":0,"fieldVector":null}}\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="allowHoverActions"\\r\\n\\r\\nfalse\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="allowPromptText"\\r\\n\\r\\ntrue\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="allowWork"\\r\\n\\r\\nfalse\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="useInlineImages"\\r\\n\\r\\ntrue\\r\\n--{boundary}\\r\\nContent-Disposition: form-data; name="telemetryCommandId"\\r\\n\\r\\nsmart{curl_data["index"]}extract\\r\\n--{boundary}--\\r\\n'
            
            response = requests.post(curl_data['url'], headers=headers, data=data, timeout=10)
            
            if response.status_code == 200 and len(response.text) > 1000:
                project_data = self.parse_api_response(response.text)
                return project_data
            else:
                print(f"⚠️ Poor API response: {response.status_code}, {len(response.text)} chars")
                
        except Exception as e:
            print(f"⚠️ API request failed: {e}")
        
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
            
            # Add metadata
            if project_data:
                project_data['api_tuple_id'] = tooltip_data.get("tupleId")
                
                # Extract government URL if present
                url_match = re.search(r'https://www\\.gov\\.uk[^"\\\\]+', html_tooltip)
                if url_match:
                    gov_url = url_match.group(0).replace('\\\\', '').replace('""', '')
                    project_data['government_url'] = unquote(gov_url)
            
            return project_data
            
        except Exception as e:
            print(f"⚠️ Response parsing failed: {e}")
            return None
    
    def parse_html_tooltip(self, html_content):
        """Parse HTML tooltip (proven method)"""
        clean_html = html.unescape(html_content)
        text_content = re.sub(r'</div>', '\\n', clean_html)
        text_content = re.sub(r'<br[^>]*>', '\\n', text_content)
        text_content = re.sub(r'<[^>]+>', '', text_content)
        
        lines = [line.strip() for line in text_content.split('\\n') if line.strip()]
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
    
    def save_all_results(self):
        """Save all extracted results"""
        print("\\n💾 Saving complete extraction results...")
        
        # Save complete dataset
        with open("smart_curl_projects.json", "w", encoding="utf-8") as f:
            json.dump(self.processed_projects, f, indent=2, ensure_ascii=False)
        
        # Calculate totals
        total_cost = 0
        total_grant = 0
        for project in self.processed_projects:
            try:
                cost = project.get('total_cost', '0').replace(',', '')
                grant = project.get('total_grant', '0').replace(',', '')
                total_cost += int(cost) if cost.isdigit() else 0
                total_grant += int(grant) if grant.isdigit() else 0
            except:
                continue
        
        # Create comprehensive summary
        summary = f"""# Smart cURL Extraction Results

## Summary Statistics
- **Projects Successfully Extracted:** {len(self.processed_projects)}
- **Total Project Value:** £{total_cost:,}
- **Total Government Grants:** £{total_grant:,}
- **Average Project Size:** £{total_cost // len(self.processed_projects) if self.processed_projects else 0:,}
- **Average Grant Amount:** £{total_grant // len(self.processed_projects) if self.processed_projects else 0:,}
- **Average Grant Percentage:** {round(total_grant / total_cost * 100, 1) if total_cost > 0 else 0}%

## Regional Distribution
"""
        
        # Count by region
        regions = {}
        for project in self.processed_projects:
            region = project.get('region', 'Unknown')
            regions[region] = regions.get(region, 0) + 1
        
        for region, count in sorted(regions.items()):
            summary += f"- **{region}:** {count} projects\\n"
        
        summary += "\\n## Industry Distribution\\n"
        
        # Count by industry
        industries = {}
        for project in self.processed_projects:
            industry = project.get('industry', 'Unknown')
            industries[industry] = industries.get(industry, 0) + 1
        
        for industry, count in sorted(industries.items()):
            summary += f"- **{industry}:** {count} projects\\n"
        
        summary += "\\n## Detailed Project List\\n\\n"
        
        for i, project in enumerate(self.processed_projects, 1):
            summary += f"### Project {i}: {project.get('company_name', 'Unknown Company')}\\n\\n"
            for key, value in project.items():
                if key not in ['source_coordinates', 'source_tuple_id', 'extraction_index', 'api_tuple_id']:
                    summary += f"- **{key.replace('_', ' ').title()}:** {value}\\n"
            summary += "\\n"
        
        with open("smart_curl_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
        
        # Create CSV for analysis
        try:
            import pandas as pd
            df = pd.DataFrame(self.processed_projects)
            df.to_csv("smart_curl_projects.csv", index=False)
            print("💾 Saved: smart_curl_projects.csv")
        except ImportError:
            print("⚠️ pandas not available for CSV export")
        
        print("💾 Saved: smart_curl_projects.json")
        print("💾 Saved: smart_curl_summary.md")
        
        print(f"\\n🎉 COMPLETE SUCCESS!")
        print(f"📊 {len(self.processed_projects)} projects extracted with £{total_cost:,} total value")

def main():
    print("🎯 Smart cURL Collector for IETF Data")
    print("=" * 60)
    print("Choose mode:")
    print("1. Interactive collection (paste cURL commands one by one)")
    print("2. Batch mode (read from curl_commands.txt file)")
    print("3. Single cURL test")
    
    mode = input("\\nEnter mode (1/2/3): ").strip()
    
    collector = SmartCurlCollector()
    
    if mode == "1":
        collector.interactive_collection_mode()
    elif mode == "2":
        collector.batch_mode()
    elif mode == "3":
        print("\\n📎 Paste a single cURL command to test:")
        curl_cmd = input().strip()
        if curl_cmd:
            parsed = collector.parse_curl_command(curl_cmd, 1)
            if parsed:
                collector.collected_curls = [parsed]
                collector.process_all_curls()
    else:
        print("❌ Invalid mode selected")

if __name__ == "__main__":
    main() 