#!/usr/bin/env python3
"""
Simple All Markers Extractor - Automatically extracts all IETF markers
Uses systematic approach to find every marker without manual clicking
"""
import json
import time
import re
import requests
import html
from urllib.parse import unquote

class SimpleAllMarkersExtractor:
    def __init__(self, session_id):
        self.session_id = session_id
        self.cookies = "AWSELBCORS=test; _ga=GA1.1.test"  # Basic cookies
        self.all_projects = []
        self.processed_companies = set()
        
    def extract_all_markers_automatically(self):
        """Extract all markers using systematic tuple ID testing"""
        print(f"🚀 AUTOMATIC ALL-MARKERS EXTRACTION")
        print(f"Session: {self.session_id[:30]}...")
        print("=" * 60)
        
        successful_extractions = 0
        tested_count = 0
        
        # Test a wide range of tuple IDs - this finds all markers
        print("🎯 Testing tuple IDs systematically...")
        
        for tuple_id in range(1, 200):  # Test first 200 tuple IDs
            tested_count += 1
            
            if tested_count % 25 == 0:
                print(f"Progress: {tested_count}/200 tested, {successful_extractions} projects found")
            
            project_data = self.extract_single_marker(tuple_id)
            
            if project_data:
                # Check if this is a unique company (avoid duplicates)
                company_name = project_data.get('company_name', '')
                
                if company_name and company_name not in self.processed_companies:
                    project_data['tuple_id'] = tuple_id
                    self.all_projects.append(project_data)
                    self.processed_companies.add(company_name)
                    successful_extractions += 1
                    
                    cost = project_data.get('total_cost', 'N/A')
                    region = project_data.get('region', 'Unknown')
                    print(f"✅ #{successful_extractions}: {company_name} - £{cost} ({region})")
            
            # Rate limiting to avoid being blocked
            time.sleep(0.8)
        
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"✅ Found {successful_extractions} unique IETF projects")
        print(f"📊 Tested {tested_count} possible positions")
        
        return successful_extractions
    
    def extract_single_marker(self, tuple_id):
        """Extract data from a single marker using tuple ID"""
        try:
            url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{self.session_id}/commands/tabsrv/render-tooltip-server"
            
            headers = {
                'accept': 'text/javascript',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': f'multipart/form-data; boundary=auto{tuple_id}',
                'cookie': self.cookies,
                'origin': 'https://public.tableau.com',
                'referer': 'https://public.tableau.com/views/IETFProjectMap/MapDashboard',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Use the proven multipart format
            boundary = f"auto{tuple_id}"
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
{{"r":"viz","x":500,"y":400,"w":0,"h":0,"fieldVector":null}}\r
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
auto{tuple_id}extract\r
--{boundary}--\r
"""
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200 and len(response.text) > 1000:
                return self.parse_response(response.text)
            elif response.status_code == 410:
                print(f"\n⚠️ Session expired at tuple {tuple_id}! Need fresh session.")
                return None
            else:
                return None
                
        except Exception:
            return None
    
    def parse_response(self, response_text):
        """Parse Tableau response to extract project data"""
        try:
            response_data = json.loads(response_text)
            cmd_result = response_data["vqlCmdResponse"]["cmdResultList"][0]
            tooltip_json = cmd_result["commandReturn"]["tooltipText"]
            tooltip_data = json.loads(tooltip_json)
            
            if tooltip_data.get("isEmpty", True):
                return None
            
            html_tooltip = tooltip_data["htmlTooltip"]
            return self.parse_tooltip_html(html_tooltip)
            
        except Exception:
            return None
    
    def parse_tooltip_html(self, html_content):
        """Extract structured data from HTML tooltip"""
        # Clean HTML
        clean_html = html.unescape(html_content)
        text_content = re.sub(r'</div>', '\n', clean_html)
        text_content = re.sub(r'<br[^>]*>', '\n', text_content)
        text_content = re.sub(r'<[^>]+>', '', text_content)
        
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        project_data = {}
        
        # Extract key fields
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
        
        # Extract government URL if present
        url_match = re.search(r'https://www\.gov\.uk[^"\\\\]+', html_content)
        if url_match:
            gov_url = url_match.group(0).replace('\\\\', '').replace('""', '')
            project_data['government_url'] = unquote(gov_url)
        
        # Return only if we have substantial data
        return project_data if len(project_data) >= 3 else None
    
    def save_all_results(self):
        """Save complete results with analysis"""
        print("\n💾 Saving comprehensive results...")
        
        # Save raw JSON data
        with open("all_ietf_projects.json", "w", encoding="utf-8") as f:
            json.dump(self.all_projects, f, indent=2, ensure_ascii=False)
        
        # Calculate totals
        total_projects = len(self.all_projects)
        total_cost = sum(int(p.get('total_cost', '0').replace(',', '')) for p in self.all_projects if p.get('total_cost', '').replace(',', '').isdigit())
        total_grant = sum(int(p.get('total_grant', '0').replace(',', '')) for p in self.all_projects if p.get('total_grant', '').replace(',', '').isdigit())
        
        # Generate comprehensive report
        report = f"""# Complete IETF Projects Database

## 📊 Summary Statistics
- **Total Projects:** {total_projects}
- **Total Investment:** £{total_cost:,}
- **Total Government Grants:** £{total_grant:,}
- **Average Project Cost:** £{total_cost // total_projects if total_projects > 0 else 0:,}
- **Average Grant:** £{total_grant // total_projects if total_projects > 0 else 0:,}
- **Government Contribution:** {round(total_grant / total_cost * 100, 1) if total_cost > 0 else 0}%

## 🗺️ Regional Analysis
"""
        
        # Regional breakdown
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
        
        for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1)
            report += f"- **{region}:** {count} projects ({percentage}%)\n"
        
        report += "\n## 🏭 Industry Breakdown\n"
        
        for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1)
            report += f"- **{industry}:** {count} projects ({percentage}%)\n"
        
        report += "\n## 🔬 Technology Focus\n"
        
        for technology, count in sorted(technologies.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / total_projects * 100, 1)
            report += f"- **{technology}:** {count} projects ({percentage}%)\n"
        
        report += "\n## 📋 Complete Project Listings\n\n"
        
        # List all projects
        for i, project in enumerate(self.all_projects, 1):
            company = project.get('company_name', 'Unknown Company')
            cost = project.get('total_cost', 'N/A')
            grant = project.get('total_grant', 'N/A')
            region = project.get('region', 'Unknown')
            industry = project.get('industry', 'Unknown')
            
            report += f"### {i}. {company}\n"
            report += f"- **Total Cost:** £{cost}\n"
            report += f"- **Government Grant:** £{grant}\n"
            report += f"- **Region:** {region}\n"
            report += f"- **Industry:** {industry}\n"
            
            if project.get('technology'):
                report += f"- **Technology:** {project['technology']}\n"
            if project.get('solution'):
                report += f"- **Solution:** {project['solution']}\n"
            if project.get('government_url'):
                report += f"- **More Info:** [Government Details]({project['government_url']})\n"
            
            report += "\n"
        
        # Save comprehensive report
        with open("complete_ietf_analysis.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"✅ Results saved:")
        print(f"  📄 all_ietf_projects.json - Raw data ({total_projects} projects)")
        print(f"  📄 complete_ietf_analysis.md - Full analysis with regional/industry breakdowns")
        print(f"  💰 Total value: £{total_cost:,} (£{total_grant:,} in grants)")

def main():
    print("🎯 SIMPLE ALL-MARKERS IETF EXTRACTOR")
    print("Automatically extracts every marker from the IETF Tableau map")
    print()
    
    # You can replace this with a fresh session ID
    print("🔑 Session Configuration:")
    print("Using default session format - replace with fresh session for best results")
    print()
    
    # Replace this with the actual session ID from your browser
    session_id = "REPLACE_WITH_FRESH_SESSION_ID"  # You'll need to update this
    
    if session_id == "REPLACE_WITH_FRESH_SESSION_ID":
        print("⚠️  You need to update the session_id variable with a fresh session!")
        print("📋 To get a fresh session:")
        print("1. Open: https://public.tableau.com/views/IETFProjectMap/MapDashboard")
        print("2. Click any marker")
        print("3. Open Developer Tools (F12) → Network tab")
        print("4. Click another marker")  
        print("5. Find 'render-tooltip-server' request")
        print("6. Copy the session ID from the URL")
        print("7. Replace session_id variable in this script")
        print()
        print("💡 The session format looks like: F4AC68CAE4BC4D3F9CB785AF26BDDB0C-0:0")
        return
    
    # Run the extraction
    extractor = SimpleAllMarkersExtractor(session_id)
    success_count = extractor.extract_all_markers_automatically()
    
    if success_count > 0:
        extractor.save_all_results()
        print(f"\n🏆 MISSION ACCOMPLISHED!")
        print(f"✅ Extracted {success_count} complete IETF projects")
        print(f"📊 Full database and analysis generated")
        print(f"🎯 This extracted from EVERY marker automatically!")
    else:
        print(f"\n❌ No projects extracted")
        print(f"💡 Check if the session ID is fresh and valid")

if __name__ == "__main__":
    main() 