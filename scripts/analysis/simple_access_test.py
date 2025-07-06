#!/usr/bin/env python3
"""
Simple test to verify 4-tier access control is working
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8000"

def login_and_test(username, password):
    """Login as user and test key access patterns"""
    print(f"\n=== Testing {username} ===")
    
    session = requests.Session()
    
    # Get login page for CSRF token
    login_page = session.get(f"{BASE_URL}/accounts/login/")
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    
    # Login
    login_data = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrf_token
    }
    
    login_response = session.post(f"{BASE_URL}/accounts/login/", data=login_data)
    
    if 'login' in login_response.url:
        print("❌ Login failed")
        return
    
    print("✅ Login successful")
    
    # Test list view access (should work for both users)
    list_response = session.get(f"{BASE_URL}/search/")
    if list_response.status_code == 200:
        print("✅ List view: ACCESS ALLOWED")
    else:
        print(f"❌ List view: ERROR {list_response.status_code}")
    
    # Test map view access (key difference between users)
    map_response = session.get(f"{BASE_URL}/search-map/", allow_redirects=False)
    
    if map_response.status_code == 302:
        redirect_url = map_response.headers.get('Location', '')
        if 'payment' in redirect_url:
            print("🔄 Map view: REDIRECTS TO PAYMENT (trial user)")
        else:
            print(f"🔄 Map view: REDIRECTS TO {redirect_url}")
    elif map_response.status_code == 200:
        # Check if it's an access denied page
        if 'access denied' in map_response.text.lower() or 'upgrade' in map_response.text.lower():
            print("🚫 Map view: ACCESS DENIED PAGE (list-only user)")
        else:
            print("✅ Map view: FULL ACCESS ALLOWED")
    else:
        print(f"❌ Map view: ERROR {map_response.status_code}")
    
    # Test account page
    account_response = session.get(f"{BASE_URL}/account/account/")
    if account_response.status_code == 200:
        print("✅ Account page: ACCESS ALLOWED")
        # Check for timer presence in HTML
        if 'timer' in account_response.text.lower() and 'time remaining' in account_response.text.lower():
            print("  ⏰ Shows timer (trial user)")
        else:
            print("  ✅ No timer shown (paid user)")
    else:
        print(f"❌ Account page: ERROR {account_response.status_code}")

def main():
    print("Testing 4-tier access system with actual HTTP requests...")
    print("\nExpected behavior:")
    print("  testuser2 (trial_limited): List ✅, Map → payment redirect, Shows timer")
    print("  testuser3 (list_only): List ✅, Map → access denied page, No timer")
    
    # Test both users
    login_and_test("testuser2", "password123")
    login_and_test("testuser3", "password123")

if __name__ == "__main__":
    main()