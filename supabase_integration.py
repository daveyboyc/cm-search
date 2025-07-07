"""
Supabase integration module for the CMR project.
This module provides direct access to Supabase for data operations.
"""
import os
import time
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Supabase PostgreSQL connection details from environment
DB_HOST = os.environ.get('SUPABASE_DB_HOST', 'your-supabase-host.pooler.supabase.com')
DB_PORT = os.environ.get('SUPABASE_DB_PORT', '6543')  # PgBouncer port for connection pooling
DB_NAME = os.environ.get('SUPABASE_DB_NAME', 'postgres')
DB_USER = os.environ.get('SUPABASE_DB_USER', 'your-supabase-user')
DB_PASSWORD = os.environ.get('SUPABASE_DB_PASSWORD', 'your-supabase-password')

def get_db_connection():
    """
    Get a PostgreSQL database connection.
    
    Returns:
        connection: PostgreSQL connection
    """
    try:
        # Connect to Supabase PostgreSQL database through PgBouncer
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            options="-c search_path=public"
        )
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def import_components_to_supabase(components_data, batch_size=100):
    """
    Import components data to Supabase.
    
    Args:
        components_data (list): List of component dictionaries
        batch_size (int): Number of components to import in each batch
        
    Returns:
        dict: Import statistics
    """
    start_time = time.time()
    supabase = get_supabase_client()
    stats = {"total": len(components_data), "imported": 0, "errors": 0, "error_details": []}
    
    logger.info(f"Importing {len(components_data)} components to Supabase")
    
    # Process in batches to avoid timeouts and rate limits
    for i in range(0, len(components_data), batch_size):
        batch = components_data[i:i+batch_size]
        try:
            # Map fields to match Supabase schema
            mapped_batch = []
            for comp in batch:
                # Convert component data to Supabase schema
                mapped_comp = {
                    "cmu_id": comp.get("CMU ID", ""),
                    "company_name": comp.get("Company Name", ""),
                    "location": comp.get("Location and Post Code", ""),
                    "description": comp.get("Description of CMU Components", ""),
                    "technology": comp.get("Generating Technology Class", ""),
                    "auction_name": comp.get("Auction Name", ""),
                    "delivery_year": comp.get("Delivery Year", ""),
                    "status": comp.get("Status", ""),
                    "derated_capacity_mw": comp.get("De-Rated Capacity", None),
                    # Add other fields as needed
                }
                mapped_batch.append(mapped_comp)
            
            # Insert data to Supabase
            result = supabase.table("components").insert(mapped_batch).execute()
            
            stats["imported"] += len(batch)
            logger.info(f"Imported batch {i//batch_size+1}/{(len(components_data)+batch_size-1)//batch_size}: {len(batch)} components")
            
        except Exception as e:
            stats["errors"] += 1
            error_detail = {"batch_start": i, "error": str(e)}
            stats["error_details"].append(error_detail)
            logger.error(f"Error importing batch {i//batch_size+1}: {e}")
    
    elapsed_time = time.time() - start_time
    stats["elapsed_time"] = elapsed_time
    logger.info(f"Import completed in {elapsed_time:.2f}s. Imported: {stats['imported']}, Errors: {stats['errors']}")
    
    return stats

def search_components_via_supabase(query, page=1, per_page=10, sort_by="relevance", sort_order="desc"):
    """
    Search components using Supabase's PostgreSQL full-text search.
    
    Args:
        query (str): Search query
        page (int): Page number
        per_page (int): Results per page
        sort_by (str): Field to sort by (relevance, location, date)
        sort_order (str): Sort order (asc, desc)
        
    Returns:
        dict: Search results and metadata
    """
    supabase = get_supabase_client()
    start_time = time.time()
    
    # Calculate offset based on page and per_page
    offset = (page - 1) * per_page
    
    try:
        # Base query builder
        supabase_query = supabase.table("components")
        
        # Apply search filter if query is provided
        if query and query.strip():
            # Handle special search types (CMU ID, location, etc.)
            if len(query) >= 3 and query.upper() == query and query.isalnum():
                # Likely a CMU ID search
                supabase_query = supabase_query.filter("cmu_id", "ilike", f"%{query}%")
            else:
                # Use PostgreSQL full-text search
                # This assumes you've set up the search_vector column in Supabase
                supabase_query = supabase_query.filter(
                    "search_vector", "@@", 
                    f"websearch_to_tsquery('english', '{query}')"
                )
                
                # Add ranking if sorting by relevance
                if sort_by == "relevance":
                    supabase_query = supabase_query.select(
                        "*", 
                        f"ts_rank(search_vector, websearch_to_tsquery('english', '{query}')) as rank"
                    )
        
        # Count total results (separate query for accurate count)
        count_query = supabase_query.select("count", count="exact")
        count_data = count_query.execute()
        total_count = count_data.count if hasattr(count_data, 'count') else 0
        
        # Apply sorting
        if sort_by == "relevance" and query.strip():
            supabase_query = supabase_query.order("rank", desc=(sort_order == "desc"))
        elif sort_by == "location":
            supabase_query = supabase_query.order("location", desc=(sort_order == "desc"))
        elif sort_by == "date":
            supabase_query = supabase_query.order("delivery_year", desc=(sort_order == "desc"))
        
        # Apply pagination
        supabase_query = supabase_query.range(offset, offset + per_page - 1)
        
        # Execute query
        response = supabase_query.execute()
        results = response.data if hasattr(response, 'data') else []
        
        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        # Format response
        response_data = {
            "components": results,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "api_time": time.time() - start_time
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error searching components via Supabase: {e}")
        return {
            "error": str(e),
            "components": [],
            "total_count": 0,
            "api_time": time.time() - start_time
        }

def build_location_groups_in_supabase():
    """
    Build and store location groups directly in Supabase.
    This replaces the Redis cache for location groups.
    
    Returns:
        dict: Statistics about the operation
    """
    supabase = get_supabase_client()
    start_time = time.time()
    stats = {"processed": 0, "groups_created": 0, "errors": 0}
    
    try:
        # First, clear existing location groups
        supabase.table("location_groups").delete().neq("id", 0).execute()
        
        # Get all components from Supabase
        response = supabase.table("components").select("*").execute()
        components = response.data if hasattr(response, 'data') else []
        
        stats["processed"] = len(components)
        logger.info(f"Retrieved {len(components)} components from Supabase")
        
        # Process components into groups
        grouped_by_location = {}
        
        for comp in components:
            location = comp.get("location", "")
            description = comp.get("description", "")
            
            # Skip components without location
            if not location:
                continue
                
            # Normalize location for grouping
            norm_location = location.lower().strip()
            norm_location = ' '.join(norm_location.replace(',', ' ').replace('.', ' ').split())
            
            # Create group key
            group_key = f"{norm_location}:{description}"
            
            # Initialize group if not exists
            if group_key not in grouped_by_location:
                grouped_by_location[group_key] = {
                    "location": location,
                    "description": description,
                    "cmu_ids": set(),
                    "auction_names": set(),
                    "components": [],
                    "active_status": False
                }
            
            # Update group info
            group = grouped_by_location[group_key]
            group["components"].append(comp["id"])
            
            if comp.get("cmu_id"):
                group["cmu_ids"].add(comp["cmu_id"])
                
            if comp.get("auction_name"):
                group["auction_names"].add(comp["auction_name"])
                
            # Check if this is an active component (2024 or later)
            delivery_year = comp.get("delivery_year", "")
            if delivery_year and delivery_year.isdigit() and int(delivery_year) >= 2024:
                group["active_status"] = True
        
        # Convert sets to lists for JSON serialization
        for key, group in grouped_by_location.items():
            group["cmu_ids"] = list(group["cmu_ids"])
            group["auction_names"] = list(group["auction_names"])
            group["component_count"] = len(group["components"])
            
        # Insert groups into Supabase
        groups_list = list(grouped_by_location.values())
        
        # Insert in batches to avoid timeouts
        batch_size = 100
        for i in range(0, len(groups_list), batch_size):
            batch = groups_list[i:i+batch_size]
            result = supabase.table("location_groups").insert(batch).execute()
            stats["groups_created"] += len(batch)
            logger.info(f"Created batch of {len(batch)} location groups in Supabase")
        
    except Exception as e:
        stats["errors"] += 1
        logger.error(f"Error building location groups in Supabase: {e}")
    
    stats["elapsed_time"] = time.time() - start_time
    logger.info(f"Completed building location groups in {stats['elapsed_time']:.2f}s")
    
    return stats

def refresh_materialized_views():
    """
    Refresh all materialized views in Supabase database.
    
    Returns:
        bool: True if successful, False otherwise
    """
    supabase = get_supabase_client()
    
    try:
        # Execute raw SQL to refresh materialized views
        # This requires rpc function to be set up in Supabase
        result = supabase.rpc(
            'refresh_materialized_views', 
            {}
        ).execute()
        
        logger.info("Successfully refreshed materialized views")
        return True
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")
        return False

# Example of how to use the module
if __name__ == "__main__":
    # This code only runs when the script is executed directly
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Test connection
        version = supabase.table("components").select("count(*)", count="exact").execute()
        print(f"Connected to Supabase. Component count: {version.count}")
        
    except Exception as e:
        print(f"Error testing Supabase connection: {e}")