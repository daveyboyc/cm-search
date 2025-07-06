#!/usr/bin/env python3
"""
Monitor Supabase egress using their Analytics API
"""
import os
import requests
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase project details (from direct_supabase_connection.py)
SUPABASE_URL = "https://vixsiceyuolxzmqijpds.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpeHNpY2V5dW9seHptcWlqcGRzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE1MDQ5NjcsImV4cCI6MjA0NzA4MDk2N30.J_EKGl_DdGkBL6gRwkILnHZCg55DJW6kz_qFJNxd-pI"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpeHNpY2V5dW9seHptcWlqcGRzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMTUwNDk2NywiZXhwIjoyMDQ3MDgwOTY3fQ.CdGPWhzwi7nZNvC7kN2I9Z5LE_AqKIWILa-lNQktXr8"

# Project ID extracted from URL
PROJECT_ID = "vixsiceyuolxzmqijpds"

def get_supabase_analytics():
    """Get analytics data from Supabase API"""
    try:
        # Analytics API endpoint
        analytics_url = f"{SUPABASE_URL}/rest/v1/analytics"
        
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info("Fetching Supabase analytics data...")
        response = requests.get(analytics_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Analytics data: {json.dumps(data, indent=2)}")
            return data
        else:
            logger.error(f"Failed to fetch analytics: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return None

def get_database_usage():
    """Get database usage statistics"""
    try:
        # Check if there's a database usage endpoint
        usage_url = f"{SUPABASE_URL}/rest/v1/database_usage"
        
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info("Fetching database usage data...")
        response = requests.get(usage_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Database usage: {json.dumps(data, indent=2)}")
            return data
        else:
            logger.warning(f"Database usage endpoint not available: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching database usage: {e}")
        return None

def check_table_sizes():
    """Check the sizes of our tables to estimate egress potential"""
    try:
        # Query table sizes
        query_url = f"{SUPABASE_URL}/rest/v1/rpc/pg_table_size_info"
        
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info("Checking table sizes...")
        
        # Try different approaches to get table size info
        # Method 1: Direct query to information_schema
        select_url = f"{SUPABASE_URL}/rest/v1/rpc/get_table_sizes"
        response = requests.post(select_url, headers=headers, json={})
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Table sizes: {json.dumps(data, indent=2)}")
            return data
        else:
            logger.warning(f"Table size function not available: {response.status_code}")
            
            # Method 2: Query our actual tables for row counts
            return query_table_counts()
            
    except Exception as e:
        logger.error(f"Error checking table sizes: {e}")
        return query_table_counts()

def query_table_counts():
    """Get row counts for our main tables"""
    try:
        logger.info("Getting table row counts...")
        
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        
        tables = ["checker_component", "checker_locationgroup", "checker_cmuregistry"]
        results = {}
        
        for table in tables:
            try:
                # Get count
                count_url = f"{SUPABASE_URL}/rest/v1/{table}?select=count"
                response = requests.get(count_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    count = len(data) if isinstance(data, list) else 0
                    results[table] = {"count": count}
                    logger.info(f"Table {table}: {count} rows")
                else:
                    logger.warning(f"Could not get count for {table}: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Error querying {table}: {e}")
                
        return results
        
    except Exception as e:
        logger.error(f"Error querying table counts: {e}")
        return {}

def estimate_egress_from_query(table_name, estimated_rows):
    """Estimate potential egress from a query"""
    # Average row sizes based on our knowledge
    row_sizes = {
        "checker_component": 1.5,  # ~1.5KB per component
        "checker_locationgroup": 2.5,  # ~2.5KB per location group (with JSON)
        "checker_cmuregistry": 0.5,   # ~0.5KB per CMU record
    }
    
    avg_size_kb = row_sizes.get(table_name, 1.0)
    estimated_mb = (estimated_rows * avg_size_kb) / 1024
    
    logger.info(f"Estimated egress for {estimated_rows} rows from {table_name}: {estimated_mb:.2f} MB")
    return estimated_mb

def monitor_recent_queries():
    """Monitor recent database activity if possible"""
    try:
        # Try to access query logs (may not be available)
        logger.info("Attempting to access query logs...")
        
        # This would require admin access which we may not have
        logs_url = f"{SUPABASE_URL}/rest/v1/pg_stat_statements"
        
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(logs_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Query statistics: {json.dumps(data[:5], indent=2)}")  # Show first 5
            return data
        else:
            logger.warning(f"Query logs not accessible: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Could not access query logs: {e}")
        return None

def main():
    """Main monitoring function"""
    logger.info("=== Supabase Egress Monitoring ===")
    
    # Try different monitoring approaches
    logger.info("\n1. Checking analytics API...")
    analytics = get_supabase_analytics()
    
    logger.info("\n2. Checking database usage...")
    usage = get_database_usage()
    
    logger.info("\n3. Checking table sizes...")
    table_info = check_table_sizes()
    
    logger.info("\n4. Monitoring recent queries...")
    query_stats = monitor_recent_queries()
    
    # Estimate potential egress based on what we know
    logger.info("\n5. Egress estimates based on known data...")
    
    # From our previous analysis:
    # - LocationGroup: 16,009 records × 2.5KB = ~38MB potential
    # - Component: Much larger dataset, varies by query
    
    logger.info("Known egress patterns:")
    logger.info("- LocationGroup queries: 2.5KB per record")
    logger.info("- Battery search returned 2,244 location groups = 5.6MB")
    logger.info("- London search returned 337 location groups = 0.8MB")
    
    estimate_egress_from_query("checker_locationgroup", 2244)  # Battery search
    estimate_egress_from_query("checker_locationgroup", 337)   # London search
    estimate_egress_from_query("checker_locationgroup", 16009) # Full table scan
    
    logger.info("\n=== Monitoring Complete ===")

if __name__ == "__main__":
    main()