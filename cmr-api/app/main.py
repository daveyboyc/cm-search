from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

from app.auth import get_api_key
from app.query_processor import process_query, connect_db, disconnect_db

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Capacity Market API",
    description="API for querying UK Capacity Market data",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await disconnect_db()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request model
class Query(BaseModel):
    query: str

@app.get("/")
async def root():
    """Root endpoint returns API info"""
    return {
        "name": "Capacity Market API",
        "version": "1.0.0",
        "description": "API for querying UK Capacity Market data"
    }

@app.post("/api/search")
async def search_database(query_data: Query, api_key: str = Depends(get_api_key)):
    """Process a natural language query and return database results"""
    try:
        results = await process_query(query_data.query)
        return {
            "status": "success",
            "query": query_data.query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")

# For OpenAPI schema compatibility with ChatGPT
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    openapi_schema = app.openapi()
    # Add servers section for ChatGPT
    openapi_schema["servers"] = [
        {"url": "https://cmr-api-service-ea80df34f49d.herokuapp.com"}
    ]
    return openapi_schema
