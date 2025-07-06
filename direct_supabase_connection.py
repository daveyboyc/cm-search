#!/usr/bin/env python3
"""
Direct connection to Supabase PostgreSQL database.
This script tests and demonstrates using direct PostgreSQL connection strings.
"""
import sys
import logging
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase PostgreSQL connection details
DB_HOST = "aws-0-eu-west-2.pooler.supabase.com"
DB_PORT = "6543"  # PgBouncer port
DB_NAME = "postgres"
DB_USER = "postgres.vixsiceyuolxzmqijpds"
DB_PASSWORD = "vzIU91Rn55qgV95y"  # Using the password from your DATABASE_URL

def test_db_connection():
    """Test connection to Supabase PostgreSQL database"""
    try:
        logger.info("Connecting to Supabase PostgreSQL database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        logger.info("Connection successful! PostgreSQL version:")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"PostgreSQL version: {version}")
        
        # Test listing tables
        logger.info("Listing tables in the database:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        if tables:
            for table in tables:
                logger.info(f"  - {table[0]}")
        else:
            logger.info("  No tables found in public schema")
            
        cursor.close()
        conn.close()
        
        logger.info("Database connection test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return False

def setup_search_index():
    """Set up full-text search in Supabase PostgreSQL database"""
    try:
        logger.info("Setting up full-text search...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Create a components table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS components (
            id SERIAL PRIMARY KEY,
            cmu_id TEXT,
            company_name TEXT,
            location TEXT,
            description TEXT,
            technology TEXT,
            auction_name TEXT,
            delivery_year TEXT,
            status TEXT,
            derated_capacity_mw NUMERIC,
            latitude NUMERIC,
            longitude NUMERIC,
            geocoded BOOLEAN DEFAULT FALSE,
            county TEXT,
            outward_code TEXT,
            search_vector TSVECTOR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
        
        # Add search_vector column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE components ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;")
        except Exception as e:
            logger.warning(f"Could not add search_vector column (might already exist): {e}")
        
        # Create search index
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS components_search_idx ON components USING GIN(search_vector);
        """)
        
        # Create trigger function
        cursor.execute("""
        CREATE OR REPLACE FUNCTION components_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector = 
                setweight(to_tsvector('english', COALESCE(NEW.company_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.county, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.outward_code, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.technology, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.cmu_id, '')), 'D') ||
                setweight(to_tsvector('english', COALESCE(NEW.auction_name, '')), 'D') ||
                setweight(to_tsvector('english', COALESCE(NEW.delivery_year, '')), 'D');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """)
        
        # Create trigger
        try:
            cursor.execute("""
            DROP TRIGGER IF EXISTS components_search_trigger ON components;
            """)
            
            cursor.execute("""
            CREATE TRIGGER components_search_trigger
            BEFORE INSERT OR UPDATE ON components
            FOR EACH ROW
            EXECUTE FUNCTION components_search_vector_update();
            """)
        except Exception as e:
            logger.warning(f"Could not create trigger (might exist or require different permissions): {e}")
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Full-text search setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up full-text search: {e}")
        return False

def import_test_data():
    """Import some test data to verify search functionality"""
    try:
        logger.info("Importing test data...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Insert some test data
        test_data = [
            {
                'cmu_id': 'TEST001',
                'company_name': 'Test Energy Ltd',
                'location': 'London Power Station, EC1A 1BB',
                'description': 'Combined cycle gas turbine power plant',
                'technology': 'CCGT',
                'auction_name': '2024-25 (T-4) Four Year Ahead Capacity Auction',
                'delivery_year': '2024',
                'status': 'Active',
                'derated_capacity_mw': 450.5
            },
            {
                'cmu_id': 'TEST002',
                'company_name': 'Green Power Solutions',
                'location': 'Manchester Energy Hub, M1 1AA',
                'description': 'Wind farm with 24 turbines',
                'technology': 'Wind',
                'auction_name': '2025-26 (T-4) Four Year Ahead Capacity Auction',
                'delivery_year': '2025',
                'status': 'Active',
                'derated_capacity_mw': 120.75
            },
            {
                'cmu_id': 'TEST003',
                'company_name': 'Vital Energy Solutions',
                'location': 'Birmingham Energy Centre, B1 1BB',
                'description': 'Battery storage facility',
                'technology': 'Battery Storage',
                'auction_name': '2023-24 (T-1) One Year Ahead Capacity Auction',
                'delivery_year': '2023',
                'status': 'Inactive',
                'derated_capacity_mw': 50.0
            }
        ]
        
        for item in test_data:
            cursor.execute("""
            INSERT INTO components 
            (cmu_id, company_name, location, description, technology, auction_name, delivery_year, status, derated_capacity_mw)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cmu_id) DO NOTHING
            """, (
                item['cmu_id'], 
                item['company_name'], 
                item['location'], 
                item['description'], 
                item['technology'], 
                item['auction_name'],
                item['delivery_year'],
                item['status'],
                item['derated_capacity_mw']
            ))
        
        # Commit changes
        conn.commit()
        
        # Verify data was inserted
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]
        logger.info(f"Total components in database: {count}")
        
        cursor.close()
        conn.close()
        
        logger.info("Test data import completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error importing test data: {e}")
        return False

def test_search_functionality():
    """Test the search functionality"""
    try:
        logger.info("Testing search functionality...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test search for 'vital'
        search_term = 'vital'
        logger.info(f"Searching for '{search_term}'...")
        
        cursor.execute("""
        SELECT id, cmu_id, company_name, location, technology, 
               ts_rank(search_vector, websearch_to_tsquery('english', %s)) as rank
        FROM components
        WHERE search_vector @@ websearch_to_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT 10
        """, (search_term, search_term))
        
        results = cursor.fetchall()
        logger.info(f"Found {len(results)} results for '{search_term}':")
        
        for row in results:
            logger.info(f"  - {row['company_name']} at {row['location']} (Rank: {row['rank']})")
        
        cursor.close()
        conn.close()
        
        logger.info("Search test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error testing search: {e}")
        return False

if __name__ == "__main__":
    # Test connection
    if not test_db_connection():
        sys.exit(1)
    
    # Setup search (only needed once)
    if not setup_search_index():
        logger.warning("Search index setup had issues, but continuing...")
    
    # Import test data
    if not import_test_data():
        logger.warning("Test data import had issues, but continuing...")
    
    # Test search
    if not test_search_functionality():
        logger.warning("Search test had issues")
        
    logger.info("All tests completed")