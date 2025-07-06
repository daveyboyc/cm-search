#!/usr/bin/env python
import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

def test_url_behavior():
    """Test actual URL behavior to see if there are any caching or frontend issues"""
    print("Testing URL behavior for DSR technology map...")
    print("=" * 60)
    
    client = Client()
    
    # Test 1: Basic DSR technology page
    print("\n1. Testing basic DSR page:")
    try:
        response = client.get('/technology/DSR/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            # Check if AXLE ENERGY appears in the response
            if 'AXLE ENERGY' in content:
                print("   ✓ AXLE ENERGY found in response")
            else:
                print("   ✗ AXLE ENERGY NOT found in response")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: DSR with status=all
    print("\n2. Testing DSR with status=all:")
    try:
        response = client.get('/technology/DSR/?status=all')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            if 'AXLE ENERGY' in content:
                print("   ✓ AXLE ENERGY found in response")
                # Count occurrences
                count = content.count('AXLE ENERGY')
                print(f"   AXLE ENERGY appears {count} times in HTML")
            else:
                print("   ✗ AXLE ENERGY NOT found in response")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: DSR with status=active
    print("\n3. Testing DSR with status=active:")
    try:
        response = client.get('/technology/DSR/?status=active')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            if 'AXLE ENERGY' in content:
                print("   ✓ AXLE ENERGY found in response")
                # Count occurrences
                count = content.count('AXLE ENERGY')
                print(f"   AXLE ENERGY appears {count} times in HTML")
            else:
                print("   ✗ AXLE ENERGY NOT found in response")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: DSR with status=inactive
    print("\n4. Testing DSR with status=inactive:")
    try:
        response = client.get('/technology/DSR/?status=inactive')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            if 'AXLE ENERGY' in content:
                print("   ✗ AXLE ENERGY found in response (unexpected!)")
                count = content.count('AXLE ENERGY')
                print(f"   AXLE ENERGY appears {count} times in HTML")
            else:
                print("   ✓ AXLE ENERGY NOT found in response (expected)")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Check map view URLs
    print("\n5. Testing DSR map view URLs:")
    map_urls = [
        '/technology/DSR/map/',
        '/technology/DSR/map/?status=all',
        '/technology/DSR/map/?status=active',
        '/technology/DSR/map/?status=inactive'
    ]
    
    for url in map_urls:
        try:
            print(f"\n   Testing: {url}")
            response = client.get(url)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                if 'AXLE ENERGY' in content:
                    print("   ✓ AXLE ENERGY found in response")
                    # Look for the location count display
                    if 'unique locations' in content:
                        import re
                        match = re.search(r'(\d+)\s+unique locations', content)
                        if match:
                            location_count = match.group(1)
                            print(f"   Shows {location_count} unique locations")
                else:
                    print("   ✗ AXLE ENERGY NOT found in response")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 6: Check if there are any encoding issues
    print("\n6. Testing URL encoding issues:")
    encoded_urls = [
        '/technology/DSR/?status=all',
        '/technology/DSR%2F?status=all',  # Over-encoded
        '/technology/DSR/?status%3Dall',  # Encoded parameter
    ]
    
    for url in encoded_urls:
        try:
            print(f"\n   Testing: {url}")
            response = client.get(url)
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("URL BEHAVIOR TEST COMPLETE")
    print("\nIf all tests show AXLE ENERGY in status=all and status=active,")
    print("but the user reports different behavior, this suggests:")
    print("1. Browser caching issues")
    print("2. CDN/proxy caching")
    print("3. User testing different URL parameters")
    print("4. JavaScript interference in the frontend")

if __name__ == "__main__":
    test_url_behavior()