import os
import sys
import json
from dotenv import load_dotenv
import openai
from typing import Dict, Any, List
import databases
import sqlalchemy

load_dotenv()

# Remove Django setup
# DJANGO_PROJECT_PATH = os.getenv("DJANGO_PROJECT_PATH")
# sys.path.append(DJANGO_PROJECT_PATH)
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capacity_checker.settings")
# import django
# django.setup()

# Remove Django model imports
# from checker.models import Component
# from django.db.models import Q, Count, Sum, Avg

# Database URL (should be set in Heroku config vars)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/database")

# Initialize database connection
database = databases.Database(DATABASE_URL)

# Define SQLAlchemy metadata (needed by 'databases' library)
metadata = sqlalchemy.MetaData()

# Define component table structure mirroring Django model (approximated)
component_table = sqlalchemy.Table(
    "checker_component",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("cmu_id", sqlalchemy.String),
    sqlalchemy.Column("technology", sqlalchemy.String),
    sqlalchemy.Column("company_name", sqlalchemy.String),
    sqlalchemy.Column("location", sqlalchemy.String),
    sqlalchemy.Column("capacity", sqlalchemy.Float), # Assuming capacity is a numeric field
    sqlalchemy.Column("derated_capacity_mw", sqlalchemy.Float),
    sqlalchemy.Column("latitude", sqlalchemy.Float),
    sqlalchemy.Column("longitude", sqlalchemy.Float),
    sqlalchemy.Column("geocoded", sqlalchemy.Boolean),
    # Add other fields if needed for queries
)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai.api_key = api_key
else:
    print("WARNING: No OpenAI API key found in environment variables")

# Define regions
REGIONS = {
    "north england": ["Yorkshire", "North East", "North West", "Cumbria", "Lancashire", 
                       "Durham", "Northumberland", "Manchester", "Liverpool", "Leeds"],
    "midlands": ["West Midlands", "East Midlands", "Staffordshire", "Derbyshire", 
                  "Leicestershire", "Birmingham", "Nottingham"],
    "south england": ["London", "South East", "South West", "Kent", "Hampshire", 
                       "Dorset", "Devon", "Cornwall", "Bristol", "Southampton"],
    "scotland": ["Scotland", "Edinburgh", "Glasgow", "Aberdeen", "Dundee"],
    "wales": ["Wales", "Cardiff", "Swansea", "Newport"],
    "northern ireland": ["Northern Ireland", "Belfast", "Derry"]
}

async def connect_db():
    """Connect to the database on startup."""
    await database.connect()
    print("Database connected.")

async def disconnect_db():
    """Disconnect from the database on shutdown."""
    await database.disconnect()
    print("Database disconnected.")


async def process_query(query_text: str) -> Dict[str, Any]:
    """Process natural language query using OpenAI to structure it"""
    
    system_message = """
    You are a helpful assistant that converts natural language queries about the UK Capacity Market 
    into structured data for database queries. Extract key parameters including:
    
    - technology_type: The energy technology being queried (e.g. "batteries", "solar", "wind", 
      "DSR", "storage", "gas", etc.)
    - region: Geographic area (e.g. "north england", "scotland", etc.)
    - company: Any specific company mentioned
    - capacity_min/capacity_max: Minimum or maximum capacity values
    - time_period: Time reference (e.g. "current", "2023")
    
    Return a JSON object with these parameters. If a parameter is not mentioned, don't include it.
    """
    
    try:
        # Ensure OpenAI client is initialized
        if not openai.api_key:
             return {"error": "OpenAI API key is not configured."}
             
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query_text}
            ]
        )
        
        parsed_query = json.loads(response.choices[0].message.content)
        return await execute_database_query(parsed_query)
    except Exception as e:
        return {"error": f"Failed to process query: {str(e)}"}

async def execute_database_query(parsed_query: Dict[str, Any]) -> Dict[str, Any]:
    """Execute database query based on the parsed parameters using 'databases' library"""
    
    # Start building the query using SQLAlchemy core
    query = component_table.select()
    filters_applied = []
    
    # Filter by technology type (case-insensitive)
    if tech_type := parsed_query.get("technology_type"):
        query = query.where(component_table.c.technology.ilike(f'%{tech_type}%'))
        filters_applied.append(f"Technology: {tech_type}")
    
    # Filter by region (case-insensitive)
    if region := parsed_query.get("region"):
        if region.lower() in REGIONS:
            location_terms = REGIONS[region.lower()]
            region_filter = sqlalchemy.or_(
                *[component_table.c.location.ilike(f'%{term}%') for term in location_terms]
            )
            query = query.where(region_filter)
            filters_applied.append(f"Region: {region}")
    
    # Filter by company (case-insensitive)
    if company := parsed_query.get("company"):
        query = query.where(component_table.c.company_name.ilike(f'%{company}%'))
        filters_applied.append(f"Company: {company}")
    
    # Filter by capacity (ensure capacity field exists in table definition)
    capacity_field = component_table.c.get('capacity') or component_table.c.get('derated_capacity_mw')
    if capacity_field is not None:
        if min_cap := parsed_query.get("capacity_min"):
            try:
                min_cap = float(min_cap)
                query = query.where(capacity_field >= min_cap)
                filters_applied.append(f"Min capacity: {min_cap}")
            except (ValueError, TypeError):
                pass
                
        if max_cap := parsed_query.get("capacity_max"):
            try:
                max_cap = float(max_cap)
                query = query.where(capacity_field <= max_cap)
                filters_applied.append(f"Max capacity: {max_cap}")
            except (ValueError, TypeError):
                pass
    
    # Get count using a separate count query
    count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(query.alias())
    count = await database.fetch_val(count_query)
    
    # If no components found, return early
    if count == 0:
        return {
            "count": 0,
            "message": "No components matched your query",
            "query_interpretation": parsed_query,
            "filters_applied": filters_applied
        }
    
    # Get aggregate data (ensure capacity field exists)
    total_capacity = 0
    avg_capacity = 0
    if capacity_field is not None:
        agg_query = sqlalchemy.select([
            sqlalchemy.func.sum(capacity_field).label('total'),
            sqlalchemy.func.avg(capacity_field).label('avg')
        ]).select_from(query.alias())
        agg_result = await database.fetch_one(agg_query)
        if agg_result:
            total_capacity = agg_result['total'] or 0
            avg_capacity = agg_result['avg'] or 0
    
    # Get technology breakdown
    tech_breakdown_query = sqlalchemy.select([
        component_table.c.technology,
        sqlalchemy.func.count().label('count')
    ]).select_from(query.alias()).group_by(component_table.c.technology)
    tech_breakdown_result = await database.fetch_all(tech_breakdown_query)
    tech_breakdown = {row['technology']: row['count'] for row in tech_breakdown_result}
    
    # Get component samples
    sample_query = query.limit(5)
    samples_result = await database.fetch_all(sample_query)
    # Convert RowProxy to list of dicts
    samples = [dict(row._mapping) for row in samples_result]
    
    # Get region distribution if requested
    region_data = {}
    if region and region.lower() in REGIONS:
        for location_term in REGIONS[region.lower()]:
            term_count_query = sqlalchemy.select([sqlalchemy.func.count()])\
                                      .select_from(query.alias())\
                                      .where(component_table.c.location.ilike(f'%{location_term}%'))
            term_count = await database.fetch_val(term_count_query)
            if term_count > 0:
                region_data[location_term] = term_count
    
    return {
        "count": count,
        "total_capacity_mw": round(float(total_capacity), 2),
        "average_capacity_mw": round(float(avg_capacity), 2),
        "samples": samples,
        "tech_breakdown": tech_breakdown,
        "region_breakdown": region_data,
        "query_interpretation": parsed_query,
        "filters_applied": filters_applied
    }
