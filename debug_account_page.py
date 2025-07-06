#!/usr/bin/env python3
"""
Debug account page to see what JavaScript variables are being set
"""
import requests
from bs4 import BeautifulSoup
import re

def debug_account_page(username, password):
    print(f"\n=== Debugging {username} account page ===")
    
    session = requests.Session()
    
    # Login first
    login_page = session.get("http://localhost:8000/accounts/login/")
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    
    login_data = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrf_token
    }
    
    login_response = session.post("http://localhost:8000/accounts/login/", data=login_data)
    
    if 'login' in login_response.url:
        print("❌ Login failed")
        return
    
    # Get account page
    account_response = session.get("http://localhost:8000/account/account/")
    html_content = account_response.text
    
    # Extract JavaScript variables
    access_level_match = re.search(r"const userAccessLevel = '([^']+)';", html_content)
    has_paid_access_match = re.search(r'"has-paid-access-data"[^>]*>([^<]+)<', html_content)
    
    if access_level_match:
        access_level = access_level_match.group(1)
        print(f"✅ userAccessLevel: '{access_level}'")
    else:
        print("❌ Could not find userAccessLevel in HTML")
    
    if has_paid_access_match:
        has_paid_access = has_paid_access_match.group(1)
        print(f"✅ has_paid_access_data: {has_paid_access}")
    else:
        print("❌ Could not find has_paid_access_data in HTML")
    
    # Check if timer logic should execute
    print(f"✅ Should show timer: {not (access_level in ['list_only', 'full'] or has_paid_access == 'true')}")
    
    # Look for timer-related HTML elements
    if 'Time remaining:' in html_content:
        print("⏰ Timer HTML found in page")
    else:
        print("✅ No timer HTML found")
    
    # Check the actual conditional logic
    if access_level == 'list_only':
        print("✅ User should see: 'List Access active. Upgrade to Full Access for map features.'")
        print("✅ accessTimerDiv should be hidden")
    elif access_level == 'full':
        print("✅ User should see: 'Full access active.'")
        print("✅ accessTimerDiv should be hidden")
    else:
        print(f"⏰ User should see timer logic (access level: {access_level})")

def main():
    debug_account_page("testuser2", "password123")
    debug_account_page("testuser3", "password123")

if __name__ == "__main__":
    main()