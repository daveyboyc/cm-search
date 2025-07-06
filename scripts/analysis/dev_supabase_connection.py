#!/usr/bin/env python3
"""
Test script to verify Supabase connection and access.
This will attempt to connect to Supabase and list tables.
"""
import sys
import logging
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase credentials
SUPABASE_URL = "https://xjqbgsyxucyobqfnvudv.supabase.co"
SUPABASE_KEY = "sbp_52a9ad3d2dee4b31a3ffe35bec9b374561860dca"

def test_rest_api_connection():
    """Test connection to Supabase REST API"""
    try:
        # Test connection by making a simple REST API call
        logger.info("Testing connection to Supabase REST API...")
        
        # Try to list tables via REST API
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/",
            headers=headers
        )
        
        if response.status_code == 200:
            logger.info(f"Connection successful! Response: {response.text}")
            return True
        else:
            logger.error(f"Failed to connect: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return False

if __name__ == "__main__":
    success = test_rest_api_connection()
    sys.exit(0 if success else 1)