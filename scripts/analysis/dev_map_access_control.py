#!/usr/bin/env python3
"""
Test script to verify map access control is working properly
Tests both URL access and template rendering for different user types
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from checker.access_control import get_user_access_level, can_access_map_view

def test_user_access_levels():
    """Test access levels for different user types"""
    print("🔍 Testing Map Access Control")
    print("=" * 50)
    
    # Test testuser2 (should be trial)
    try:
        testuser2 = User.objects.get(username='testuser2')
        access_level = get_user_access_level(testuser2)
        can_access_maps = can_access_map_view(testuser2)
        
        print(f"👤 testuser2:")
        print(f"   Access Level: {access_level}")
        print(f"   Can Access Maps: {can_access_maps}")
        print(f"   Expected: access_level='trial', can_access_maps=False")
        
        if access_level == 'trial' and can_access_maps == False:
            print("   ✅ CORRECT - Trial user blocked from maps")
        else:
            print("   ❌ INCORRECT - Trial user should be blocked")
            
    except User.DoesNotExist:
        print("❌ testuser2 not found")
    
    print()
    
    # Test admin/staff user
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            access_level = get_user_access_level(admin_user)
            can_access_maps = can_access_map_view(admin_user)
            
            print(f"👤 {admin_user.username} (admin):")
            print(f"   Access Level: {access_level}")
            print(f"   Can Access Maps: {can_access_maps}")
            print(f"   Expected: access_level='full', can_access_maps=True")
            
            if access_level == 'full' and can_access_maps == True:
                print("   ✅ CORRECT - Admin has full access")
            else:
                print("   ❌ INCORRECT - Admin should have full access")
        else:
            print("❌ No admin user found")
    except Exception as e:
        print(f"❌ Error testing admin user: {e}")
    
    print()
    
    # Test unauthenticated user
    from django.contrib.auth.models import AnonymousUser
    anon_user = AnonymousUser()
    access_level = get_user_access_level(anon_user)
    can_access_maps = can_access_map_view(anon_user)
    
    print(f"👤 Anonymous user:")
    print(f"   Access Level: {access_level}")
    print(f"   Can Access Maps: {can_access_maps}")
    print(f"   Expected: access_level='unauthenticated', can_access_maps=False")
    
    if access_level == 'unauthenticated' and can_access_maps == False:
        print("   ✅ CORRECT - Unauthenticated user blocked from maps")
    else:
        print("   ❌ INCORRECT - Unauthenticated user should be blocked")
    
    print()
    
    # Test URLs that should be protected
    print("🔗 Map URLs that should be protected:")
    protected_urls = [
        '/map/',
        '/search-map/',
        '/map_search/',
        '/map_results/',
        '/company-map/test/',
        '/technology-map/Battery/'
    ]
    
    for url in protected_urls:
        print(f"   {url} - Should redirect trial users to access denied page")
    
    print()
    print("🎯 To test:")
    print("1. Login as testuser2 and try to access map URLs")
    print("2. Look for padlock icons on map buttons")
    print("3. Verify access denied page shows for trial users")
    print("4. Verify admin/staff users can access maps normally")

if __name__ == "__main__":
    test_user_access_levels()