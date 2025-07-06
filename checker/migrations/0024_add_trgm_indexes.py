# Generated migration to add trigram indexes for fast text search

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0023_add_enhanced_places_api_fields'),
    ]

    operations = [
        migrations.RunSQL(
            # Create GIN trigram indexes for text search on LocationGroup
            sql=[
                # Ensure pg_trgm extension is enabled (idempotent)
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
                
                # Create trigram index on location field for fast ILIKE searches
                "CREATE INDEX IF NOT EXISTS locationgroup_location_trgm_idx ON checker_locationgroup USING GIN (location gin_trgm_ops);",
                
                # Create trigram index on county field
                "CREATE INDEX IF NOT EXISTS locationgroup_county_trgm_idx ON checker_locationgroup USING GIN (county gin_trgm_ops);",
                
                # Also add trigram indexes for Component table text fields
                "CREATE INDEX IF NOT EXISTS component_location_trgm_idx ON checker_component USING GIN (location gin_trgm_ops);",
                
                "CREATE INDEX IF NOT EXISTS component_description_trgm_idx ON checker_component USING GIN (description gin_trgm_ops);",
                
                "CREATE INDEX IF NOT EXISTS component_company_name_trgm_idx ON checker_component USING GIN (company_name gin_trgm_ops);",
                
                "CREATE INDEX IF NOT EXISTS component_technology_trgm_idx ON checker_component USING GIN (technology gin_trgm_ops);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS locationgroup_location_trgm_idx;",
                "DROP INDEX IF EXISTS locationgroup_county_trgm_idx;",
                "DROP INDEX IF EXISTS component_location_trgm_idx;",
                "DROP INDEX IF EXISTS component_description_trgm_idx;",
                "DROP INDEX IF EXISTS component_company_name_trgm_idx;",
                "DROP INDEX IF EXISTS component_technology_trgm_idx;",
            ]
        ),
    ]