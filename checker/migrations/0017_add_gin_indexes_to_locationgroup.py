# Generated migration for GIN indexes on LocationGroup JSON fields

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0016_add_is_active_to_locationgroup'),
    ]

    operations = [
        migrations.RunSQL(
            # Create GIN indexes for JSON field searches
            sql=[
                # Index for searching within companies JSON field
                "CREATE INDEX IF NOT EXISTS locationgroup_companies_gin_idx ON checker_locationgroup USING GIN (companies);",
                
                # Index for searching within technologies JSON field  
                "CREATE INDEX IF NOT EXISTS locationgroup_technologies_gin_idx ON checker_locationgroup USING GIN (technologies);",
                
                # Index for searching within descriptions JSON field
                "CREATE INDEX IF NOT EXISTS locationgroup_descriptions_gin_idx ON checker_locationgroup USING GIN (descriptions);",
                
                # Index for searching within auction_years JSON field
                "CREATE INDEX IF NOT EXISTS locationgroup_auction_years_gin_idx ON checker_locationgroup USING GIN (auction_years);",
                
                # Index for searching within cmu_ids JSON field
                "CREATE INDEX IF NOT EXISTS locationgroup_cmu_ids_gin_idx ON checker_locationgroup USING GIN (cmu_ids);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS locationgroup_companies_gin_idx;",
                "DROP INDEX IF EXISTS locationgroup_technologies_gin_idx;",
                "DROP INDEX IF EXISTS locationgroup_descriptions_gin_idx;",
                "DROP INDEX IF EXISTS locationgroup_auction_years_gin_idx;",
                "DROP INDEX IF EXISTS locationgroup_cmu_ids_gin_idx;",
            ]
        ),
    ]
