#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

print("🔍 Resetting search counts for all users...")

# This script clears browser localStorage search counts
# Since the counts are stored in browser storage, this creates a JavaScript snippet
# that users can run in their browser console to reset counts

js_reset_script = """
// Reset search counts for all users
console.log('Clearing all search count data...');

// Get all localStorage keys that contain search data
const keys = Object.keys(localStorage);
const searchKeys = keys.filter(k => k.includes('trialSearches_'));

console.log('Found search keys:', searchKeys);

// Remove all search count data
searchKeys.forEach(key => {
    localStorage.removeItem(key);
    console.log('Removed:', key);
});

// Also clear search popup flags from sessionStorage
const sessionKeys = Object.keys(sessionStorage);
const popupKeys = sessionKeys.filter(k => k.includes('searchLimitPopupShown'));
popupKeys.forEach(key => {
    sessionStorage.removeItem(key);
    console.log('Removed popup flag:', key);
});

console.log('✅ All search counts reset! Refresh the page to see changes.');
"""

print("📋 JavaScript snippet to reset search counts:")
print("=" * 60)
print(js_reset_script)
print("=" * 60)
print("\n🔧 To reset search counts:")
print("1. Open browser developer tools (F12)")
print("2. Go to Console tab")
print("3. Copy and paste the JavaScript above")
print("4. Press Enter")
print("5. Refresh the account page")
print("\n🌐 Or visit: http://localhost:8000/static/clear_timer_session.html")
print("   And click 'Clear Search Count Only'")