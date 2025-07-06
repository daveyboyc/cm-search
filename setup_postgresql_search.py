#!/usr/bin/env python3
"""
Script to enable full-text search in your PostgreSQL database.
This script uses your existing Django database connection.
"""
import os
import sys
import logging
import django
from django.db import connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmr.settings')
django.setup()

# SQL Statements for setting up full-text search
CREATE_SEARCH_VECTOR_COLUMN = """
ALTER TABLE checker_component ADD COLUMN IF NOT EXISTS search_vector tsvector;
"""

CREATE_SEARCH_INDEX = """
CREATE INDEX IF NOT EXISTS component_search_idx ON checker_component USING GIN(search_vector);
"""

CREATE_SEARCH_VECTOR_TRIGGER = """
CREATE OR REPLACE FUNCTION component_search_vector_update() RETURNS trigger AS $$
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

DROP TRIGGER IF EXISTS component_search_trigger ON checker_component;

CREATE TRIGGER component_search_trigger
BEFORE INSERT OR UPDATE ON checker_component
FOR EACH ROW
EXECUTE FUNCTION component_search_vector_update();
"""

UPDATE_EXISTING_RECORDS = """
UPDATE checker_component
SET search_vector = 
    setweight(to_tsvector('english', COALESCE(company_name, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(location, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(county, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(outward_code, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(technology, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(cmu_id, '')), 'D') ||
    setweight(to_tsvector('english', COALESCE(auction_name, '')), 'D') ||
    setweight(to_tsvector('english', COALESCE(delivery_year, '')), 'D')
WHERE search_vector IS NULL;
"""

def setup_full_text_search():
    """
    Set up full-text search in the PostgreSQL database.
    Uses the existing Django database connection.
    """
    try:
        # Create search vector column
        logger.info("Adding search_vector column to component table...")
        with connection.cursor() as cursor:
            cursor.execute(CREATE_SEARCH_VECTOR_COLUMN)
        
        # Create GIN index
        logger.info("Creating search index...")
        with connection.cursor() as cursor:
            cursor.execute(CREATE_SEARCH_INDEX)
        
        # Create trigger for automatic updates
        logger.info("Creating trigger for automatic search vector updates...")
        with connection.cursor() as cursor:
            cursor.execute(CREATE_SEARCH_VECTOR_TRIGGER)
        
        # Update existing records
        logger.info("Updating search vectors for existing records...")
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_EXISTING_RECORDS)
            count = cursor.rowcount
            logger.info(f"Updated {count} records with search vectors")
        
        logger.info("Full-text search setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up full-text search: {e}")
        return False

if __name__ == "__main__":
    success = setup_full_text_search()
    sys.exit(0 if success else 1)