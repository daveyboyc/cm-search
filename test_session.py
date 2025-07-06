#!/usr/bin/env python3
"""
Session Tester - Quick test for Tableau session validity
"""
import requests
import sys

def test_session(session_id):
    url = f"https://public.tableau.com/vizql/w/IETFProjectMap/v/MapDashboard/sessions/{session_id}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Session {session_id} is VALID")
            return True
        elif response.status_code == 410:
            print(f"❌ Session {session_id} is EXPIRED")
            return False
        else:
            print(f"⚠️ Session {session_id} status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    else:
        session_id = input("Enter session ID: ")
    
    test_session(session_id)
