#!/usr/bin/env python3
"""
Test script to verify 4-tier access system behavior
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_user_access(username, password):
    """Test access patterns for a specific user"""
    print(f"\n=== Testing {username} ===")
    
    # Create session
    session = requests.Session()
    
    # Get login page to get CSRF token
    login_page = session.get(f"{BASE_URL}/accounts/login/")
    if login_page.status_code != 200:
        print(f"❌ Could not access login page: {login_page.status_code}")
        return
    
    # Extract CSRF token
    csrf_token = None
    for line in login_page.text.split('\n'):
        if 'csrfmiddlewaretoken' in line and 'value=' in line:
            csrf_token = line.split('value="')[1].split('"')[0]
            break
    
    if not csrf_token:
        print("❌ Could not find CSRF token")
        return
    
    # Login
    login_data = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrf_token
    }
    
    login_response = session.post(f"{BASE_URL}/accounts/login/", data=login_data)
    
    # Check if login was successful (should redirect or show success)
    if login_response.status_code == 200 and 'login' in login_response.url:
        print("❌ Login failed")
        return
    
    print("✅ Login successful")
    
    # Test different URL access patterns
    test_urls = [
        ("/", "Home page"),
        ("/account/account/", "Account page"),
        ("/search/", "Search page"),
        ("/search-map/", "Map search page"),
        ("/search/components/", "Component search page"),
    ]
    
    for url, description in test_urls:
        try:
            response = session.get(f"{BASE_URL}{url}", allow_redirects=False)
            if response.status_code == 302:
                redirect_url = response.headers.get('Location', '')
                print(f"  {description}: REDIRECT → {redirect_url}")
            elif response.status_code == 200:
                print(f"  {description}: ✅ ACCESS ALLOWED")
            else:
                print(f"  {description}: ❌ ERROR {response.status_code}")
        except Exception as e:
            print(f"  {description}: ❌ EXCEPTION {str(e)}")

def main():
    print("Testing 4-tier access system...")
    print("Expected behavior:")
    print("  testuser2 (trial_limited): List access ✅, Map access → payment redirect")
    print("  testuser3 (list_only): List access ✅, Map access → access denied page")
    print("  admin (full): All access ✅")
    
    # Test each user
    test_user_access("testuser2", "password123")
    test_user_access("testuser3", "password123")
    
    # Test admin if available
    try:
        test_user_access("admin", "admin123")
    except:
        print("\n=== Admin user not available for testing ===")

if __name__ == "__main__":
    main()