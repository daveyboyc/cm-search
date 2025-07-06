from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import re

options = Options()
options.add_argument('--window-size=1920,1080')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

url = 'https://public.tableau.com/views/IETFProjectMap/MapDashboard?:showVizHome=no'
print('Loading page...')
driver.get(url)
time.sleep(50)  # Wait for content to load

# Get all text
text_content = driver.execute_script('return document.body.innerText;')
print(f'Page text length: {len(text_content)}')

# Look for organization patterns
patterns = [
    r'[A-Z][a-z]+ (Foundation|Project|Initiative|University|Institute|Research|Company|Corporation|Ltd|Inc)',
    r'IETF[^\n]*',
    r'Internet[^\n]*'
]

matches = []
for pattern in patterns:
    found = re.findall(pattern, text_content, re.IGNORECASE)
    matches.extend(found[:10])

print(f'Found {len(matches)} potential project mentions')
for i, match in enumerate(matches[:5]):
    print(f'  {i}: {match[:60]}...')

# Save all text
with open('ietf_page_text.txt', 'w') as f:
    f.write(text_content)

# Save matches  
with open('ietf_text_matches.json', 'w') as f:
    json.dump(matches, f, indent=2)

driver.quit()
print('Saved to ietf_page_text.txt and ietf_text_matches.json') 