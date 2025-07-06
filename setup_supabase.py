#!/usr/bin/env python3
"""
Script to set up initial Supabase database structure and functions.
Run this once to prepare your Supabase instance for the CMR application.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    from supabase_integration import get_supabase_client
except ImportError:
    logger.error("Failed to import supabase_integration. Please make sure it's installed.")
    sys.exit(1)

# SQL Statements for setting up Supabase
CREATE_COMPONENTS_TABLE = """
CREATE TABLE IF NOT EXISTS components (
    id BIGSERIAL PRIMARY KEY,
    cmu_id TEXT,
    company_name TEXT,
    location TEXT,
    description TEXT,
    technology TEXT,
    auction_name TEXT,
    delivery_year TEXT,
    status TEXT,
    type TEXT,
    derated_capacity_mw NUMERIC,
    latitude NUMERIC,
    longitude NUMERIC,
    geocoded BOOLEAN DEFAULT FALSE,
    county TEXT,
    outward_code TEXT,
    search_vector TSVECTOR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS components_cmu_id_idx ON components(cmu_id);
CREATE INDEX IF NOT EXISTS components_company_name_idx ON components(company_name);
CREATE INDEX IF NOT EXISTS components_technology_idx ON components(technology);
CREATE INDEX IF NOT EXISTS components_location_idx ON components(location);
CREATE INDEX IF NOT EXISTS components_county_outward_idx ON components(county, outward_code);

-- Full-text search index
CREATE INDEX IF NOT EXISTS components_search_idx ON components USING GIN(search_vector);
"""

CREATE_LOCATION_GROUPS_TABLE = """
CREATE TABLE IF NOT EXISTS location_groups (
    id BIGSERIAL PRIMARY KEY,
    location TEXT,
    description TEXT,
    cmu_ids JSONB,
    auction_names JSONB,
    components JSONB,
    active_status BOOLEAN DEFAULT FALSE,
    component_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS location_groups_location_idx ON location_groups(location);
CREATE INDEX IF NOT EXISTS location_groups_active_idx ON location_groups(active_status);
"""

CREATE_SEARCH_VECTOR_TRIGGER = """
-- Function to update search vector
CREATE OR REPLACE FUNCTION update_search_vector() 
RETURNS TRIGGER AS $$
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

-- Trigger to automatically update search vector
CREATE TRIGGER update_components_search_vector
BEFORE INSERT OR UPDATE ON components
FOR EACH ROW
EXECUTE FUNCTION update_search_vector();
"""

CREATE_GEOCODE_FUNCTION = """
-- Create geocoding function that uses Google Maps API
CREATE OR REPLACE FUNCTION geocode_components(max_components INTEGER DEFAULT 500)
RETURNS JSONB AS $$
DECLARE
    api_url TEXT := 'https://maps.googleapis.com/maps/api/geocode/json';
    api_key TEXT := current_setting('app.google_maps_api_key', true);
    component RECORD;
    response JSONB;
    result JSONB;
    location JSONB;
    stats JSONB := '{"processed": 0, "geocoded": 0, "errors": 0}';
    http_response JSONB;
BEGIN
    -- Check if API key is configured
    IF api_key IS NULL THEN
        RAISE EXCEPTION 'Google Maps API key is not configured';
    END IF;

    -- Loop through components that need geocoding
    FOR component IN 
        SELECT id, location 
        FROM components 
        WHERE geocoded = false AND location IS NOT NULL AND location != ''
        LIMIT max_components
    LOOP
        stats := stats || ('{"processed": ' || (stats->>'processed')::int + 1 || '}')::JSONB;
        
        -- Skip empty locations
        IF component.location IS NULL OR component.location = '' THEN
            CONTINUE;
        END IF;
        
        BEGIN
            -- Call Google Maps API
            SELECT
                content::JSONB INTO http_response
            FROM
                http((
                    'GET',
                    api_url || '?address=' || urlencode(component.location) || '&key=' || api_key || '&region=uk',
                    ARRAY[ARRAY['Content-Type', 'application/json']],
                    NULL,
                    NULL
                )::http_request);
                
            -- Process response
            IF http_response->>'status' = 'OK' THEN
                -- Extract coordinates
                location := http_response->'results'->0->'geometry'->'location';
                
                -- Update component with coordinates
                UPDATE components 
                SET 
                    latitude = (location->>'lat')::NUMERIC,
                    longitude = (location->>'lng')::NUMERIC,
                    geocoded = true
                WHERE id = component.id;
                
                stats := stats || ('{"geocoded": ' || (stats->>'geocoded')::int + 1 || '}')::JSONB;
            ELSE
                -- Log error
                RAISE NOTICE 'Geocoding error for component %: %', 
                    component.id, 
                    http_response->>'status';
                    
                stats := stats || ('{"errors": ' || (stats->>'errors')::int + 1 || '}')::JSONB;
            END IF;
            
            -- Sleep briefly to avoid rate limits
            PERFORM pg_sleep(0.2);
            
        EXCEPTION WHEN OTHERS THEN
            -- Handle exceptions
            RAISE NOTICE 'Exception geocoding component %: %', 
                component.id, 
                SQLERRM;
                
            stats := stats || ('{"errors": ' || (stats->>'errors')::int + 1 || '}')::JSONB;
        END;
    END LOOP;
    
    RETURN stats;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

CREATE_REBUILD_SEARCH_INDEX_FUNCTION = """
-- Function to rebuild search index for all components
CREATE OR REPLACE FUNCTION rebuild_search_index() 
RETURNS JSONB AS $$
DECLARE
    processed INTEGER := 0;
BEGIN
    -- Use a direct SQL UPDATE for efficiency
    UPDATE components
    SET search_vector = 
        setweight(to_tsvector('english', COALESCE(company_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(location, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(county, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(outward_code, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(technology, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(cmu_id, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(auction_name, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(delivery_year, '')), 'D');
    
    GET DIAGNOSTICS processed = ROW_COUNT;
    
    RETURN json_build_object(
        'processed', processed
    )::JSONB;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

CREATE_VIEWS = """
-- Create materialized view for component counts by technology
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_technology_stats AS
SELECT 
    technology, 
    COUNT(*) as component_count,
    COUNT(DISTINCT company_name) as company_count,
    SUM(derated_capacity_mw) as total_capacity
FROM components
WHERE technology IS NOT NULL AND technology != ''
GROUP BY technology
ORDER BY component_count DESC;

-- Create materialized view for component counts by company
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_company_stats AS
SELECT 
    company_name, 
    COUNT(*) as component_count,
    COUNT(DISTINCT technology) as technology_count,
    SUM(derated_capacity_mw) as total_capacity
FROM components
WHERE company_name IS NOT NULL AND company_name != ''
GROUP BY company_name
ORDER BY component_count DESC;

-- Create materialized view for map data
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_map_data AS
SELECT 
    id,
    location,
    technology,
    company_name,
    latitude,
    longitude,
    derated_capacity_mw,
    delivery_year
FROM components
WHERE 
    geocoded = true 
    AND latitude IS NOT NULL 
    AND longitude IS NOT NULL;

-- Create view refresh function
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_technology_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_company_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_map_data;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

def execute_sql(sql, description):
    """Execute SQL statement on Supabase database"""
    supabase = get_supabase_client()
    try:
        logger.info(f"Executing: {description}")
        result = supabase.rpc('run_sql_query', {"query": sql}).execute()
        logger.info(f"Completed: {description}")
        return True
    except Exception as e:
        logger.error(f"Error executing {description}: {e}")
        return False

def main():
    """Setup Supabase database structure"""
    logger.info("Setting up Supabase database for CMR application")
    
    # Set up Supabase client
    try:
        supabase = get_supabase_client()
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        sys.exit(1)
    
    # Create tables
    if execute_sql(CREATE_COMPONENTS_TABLE, "Creating components table"):
        logger.info("Components table created or verified")
    else:
        logger.error("Failed to create components table")
        
    if execute_sql(CREATE_LOCATION_GROUPS_TABLE, "Creating location groups table"):
        logger.info("Location groups table created or verified")
    else:
        logger.error("Failed to create location groups table")
    
    # Create triggers and functions
    if execute_sql(CREATE_SEARCH_VECTOR_TRIGGER, "Creating search vector trigger"):
        logger.info("Search vector trigger created")
    else:
        logger.error("Failed to create search vector trigger")
        
    if execute_sql(CREATE_GEOCODE_FUNCTION, "Creating geocoding function"):
        logger.info("Geocoding function created")
    else:
        logger.error("Failed to create geocoding function")
        
    if execute_sql(CREATE_REBUILD_SEARCH_INDEX_FUNCTION, "Creating search index rebuild function"):
        logger.info("Search index rebuild function created")
    else:
        logger.error("Failed to create search index rebuild function")
    
    # Create materialized views
    if execute_sql(CREATE_VIEWS, "Creating materialized views"):
        logger.info("Materialized views created")
    else:
        logger.error("Failed to create materialized views")
    
    logger.info("Supabase setup completed")

if __name__ == "__main__":
    main()