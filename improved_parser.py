#!/usr/bin/env python3
"""
Improved IETF Parser - Better HTML tooltip parsing
"""
import json
import re
import html
from urllib.parse import unquote

def debug_html_parsing():
    """Debug the HTML parsing step by step"""
    
    print("🔍 Debug HTML Parsing")
    print("=" * 40)
    
    # Load the raw response
    with open("ietf_response.txt", "r", encoding="utf-8") as f:
        response_text = f.read()
    
    response_data = json.loads(response_text)
    cmd_result = response_data["vqlCmdResponse"]["cmdResultList"][0]
    tooltip_json = cmd_result["commandReturn"]["tooltipText"]
    tooltip_data = json.loads(tooltip_json)
    html_tooltip = tooltip_data["htmlTooltip"]
    
    print("📝 Original HTML tooltip length:", len(html_tooltip))
    
    # Save the raw HTML for inspection
    with open("raw_tooltip.html", "w", encoding="utf-8") as f:
        f.write(html_tooltip)
    print("💾 Saved raw_tooltip.html")
    
    # Unescape HTML
    clean_html = html.unescape(html_tooltip)
    
    # More robust text extraction
    # Replace HTML tags with line breaks to preserve structure
    text_content = re.sub(r'</div>', '\n', clean_html)
    text_content = re.sub(r'<br[^>]*>', '\n', text_content)
    text_content = re.sub(r'<[^>]+>', '', text_content)
    
    # Clean up and split lines
    lines = text_content.split('\n')
    clean_lines = []
    
    for line in lines:
        clean_line = line.strip()
        if clean_line and clean_line not in ['', ' ', '\xa0']:
            clean_lines.append(clean_line)
    
    print(f"\n📄 Extracted {len(clean_lines)} text lines:")
    for i, line in enumerate(clean_lines, 1):
        print(f"{i:2d}: {line}")
    
    # Now parse with improved patterns
    project_data = parse_lines(clean_lines)
    
    # Extract government URL separately
    url_match = re.search(r'https://www\.gov\.uk[^"\\]+', html_tooltip)
    if url_match:
        gov_url = url_match.group(0)
        # Clean up escaped characters
        gov_url = gov_url.replace('\\', '').replace('""', '')
        project_data['government_url'] = gov_url
        print(f"🔗 Government URL: {gov_url}")
    
    return project_data

def parse_lines(lines):
    """Parse the cleaned text lines into structured data"""
    
    project_data = {}
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Company name (usually the first line with Ltd/Limited/etc)
        if not project_data.get('company_name') and re.search(r'(Ltd|Limited|PLC|Group|Company)', line, re.IGNORECASE):
            project_data['company_name'] = line
            print(f"✅ Company: {line}")
        
        # Field patterns
        elif line.startswith('Industry:'):
            project_data['industry'] = line.replace('Industry:', '').strip()
            print(f"✅ Industry: {project_data['industry']}")
            
        elif line.startswith('Competition:'):
            project_data['competition'] = line.replace('Competition:', '').strip()
            print(f"✅ Competition: {project_data['competition']}")
            
        elif line.startswith('Region:'):
            project_data['region'] = line.replace('Region:', '').strip()
            print(f"✅ Region: {project_data['region']}")
            
        elif line.startswith('Project type:'):
            project_data['project_type'] = line.replace('Project type:', '').strip()
            print(f"✅ Project Type: {project_data['project_type']}")
            
        elif line.startswith('Technology:'):
            project_data['technology'] = line.replace('Technology:', '').strip()
            print(f"✅ Technology: {project_data['technology']}")
            
        elif line.startswith('Solution:'):
            project_data['solution'] = line.replace('Solution:', '').strip()
            print(f"✅ Solution: {project_data['solution']}")
            
        elif line.startswith('Total cost:'):
            cost_match = re.search(r'£?([0-9,]+)', line)
            if cost_match:
                project_data['total_cost'] = cost_match.group(1)
                print(f"✅ Total Cost: £{project_data['total_cost']}")
                
        elif line.startswith('Total grant:'):
            grant_match = re.search(r'£?([0-9,]+)', line)
            if grant_match:
                project_data['total_grant'] = grant_match.group(1)
                print(f"✅ Total Grant: £{project_data['total_grant']}")
                
        elif line.startswith('Contractors:'):
            contractors = line.replace('Contractors:', '').strip()
            if contractors:
                project_data['contractors'] = contractors
                print(f"✅ Contractors: {contractors}")
                
        elif line.startswith('Project partners:'):
            partners = line.replace('Project partners:', '').strip()
            if partners:
                project_data['project_partners'] = partners
                print(f"✅ Project Partners: {partners}")
        
        # Long description text (typically at the end)
        elif len(line) > 80 and not any(x in line for x in ['Industry:', 'Competition:', 'Region:', 'Project type:', 'Technology:', 'Solution:', 'Total cost:', 'Total grant:']):
            if 'description' not in project_data:
                project_data['description'] = line
                print(f"✅ Description: {line[:100]}...")
            else:
                project_data['description'] += ' ' + line
        
        i += 1
    
    return project_data

def main():
    print("🌐 Improved IETF Parser")
    print("🎯 Better HTML tooltip parsing")
    print("=" * 50)
    
    project_data = debug_html_parsing()
    
    # Save the improved data
    with open("improved_project_data.json", "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)
    print("💾 Saved: improved_project_data.json")
    
    # Create a nice summary
    print(f"\n📊 FINAL EXTRACTED DATA:")
    print(f"=" * 40)
    for key, value in project_data.items():
        if key == 'description':
            print(f"{key}: {value[:100]}...")
        else:
            print(f"{key}: {value}")

if __name__ == "__main__":
    main() 