# CMR Direct Supabase PostgreSQL Integration

This guide explains how to use direct PostgreSQL connection to your Supabase database for the CMR application.

## Connection Details

We've successfully connected to your Supabase PostgreSQL database with the following settings:

```python
# Supabase PostgreSQL connection details
DB_HOST = "aws-0-eu-west-2.pooler.supabase.com"
DB_PORT = "6543"  # PgBouncer port for connection pooling
DB_NAME = "postgres"
DB_USER = "postgres.vixsiceyuolxzmqijpds"
DB_PASSWORD = "vzIU91Rn55qgV95y"
```

## How to Use

### 1. Connect to the Database

```python
import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to the database
conn = psycopg2.connect(
    host="aws-0-eu-west-2.pooler.supabase.com",
    port="6543",
    dbname="postgres",
    user="postgres.vixsiceyuolxzmqijpds",
    password="vzIU91Rn55qgV95y",
    options="-c search_path=public"
)
```

### 2. Query the Database

```python
# Execute a query
with conn.cursor(cursor_factory=RealDictCursor) as cursor:
    cursor.execute("SELECT * FROM checker_component LIMIT 10")
    results = cursor.fetchall()
    
    for row in results:
        print(f"Component: {row['id']} - {row['location']}")
```

### 3. Update Records

```python
# Update records
with conn.cursor() as cursor:
    cursor.execute(
        "UPDATE checker_component SET description = %s WHERE id = %s",
        ("New description", 123)
    )
    conn.commit()
```

## Available Scripts

We've created several scripts to help you work with your Supabase database:

1. **direct_supabase_connection.py**
   - Tests connection to your Supabase database
   - Sets up full-text search capabilities
   - Imports test data
   - Tests search functionality

2. **supabase_integration.py**
   - Main module for Supabase integration
   - Includes functions for importing components, searching, etc.
   - Uses direct PostgreSQL connection for better performance

3. **update_with_supabase.py**
   - Consolidated script for updating your database
   - Geocodes components
   - Rebuilds search indexes
   - Updates materialized views

## Performance Benefits

Using direct PostgreSQL connection offers several advantages:

1. **Lower Latency**: Direct database access without REST API overhead
2. **Better Performance**: Native PostgreSQL features like full-text search
3. **More Control**: Advanced SQL features and transactions
4. **Reduced Bandwidth**: Process data at the database level

## Maintenance Tips

1. **Connection Pooling**
   - We're using PgBouncer (port 6543) for efficient connection pooling
   - This allows many concurrent connections without overwhelming the database

2. **Migrations**
   - For schema changes, use the direct connection (port 5432)
   - For normal operations, use PgBouncer (port 6543)

3. **Regular Maintenance**
   - Run `VACUUM ANALYZE` periodically to maintain performance
   - Rebuild indexes when necessary with `REINDEX`

## Troubleshooting

### Connection Issues

- **Permissions**: Check if your IP is allowed in Supabase's network restrictions
- **Resources**: Check if you've hit your project's connection limits
- **Downtime**: Supabase may have scheduled maintenance

### Query Performance

- **Slow Queries**: Add appropriate indexes to your tables
- **Connection Pooling**: Check PgBouncer settings for optimal performance

### Future Work

You can further optimize your application by:

1. Creating materialized views for common queries
2. Setting up database-level triggers for data integrity
3. Implementing row-level security for better access control
4. Using PostgreSQL's LISTEN/NOTIFY for real-time updates