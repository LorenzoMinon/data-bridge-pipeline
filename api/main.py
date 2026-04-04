# main.py
# FastAPI bridge endpoint 
# serves clean company data to clients.
# This is the redistribution layer: provider data, cleaned, served as our own API.

import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

# Postgres config
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_DB = os.getenv("PG_DB", "pipeline_db")
PG_USER = os.getenv("PG_USER", "pipeline_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "pipeline_pass")

app = FastAPI(
    title="Data Bridge API",
    description="Clean company data, ready for redistribution.",
    version="1.0.0"
)


def get_db_connection():
    """Open and return a Postgres connection."""
    return psycopg2.connect(
        host=PG_HOST,
        port=int(PG_PORT),
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )
    
# 3 endpoints. MOST IMPORTANT PART!

@app.get("/health")
def health_check():
    #check if the api is alive
    return {"status": "ok", "service": "data-bridge-api"}

@app.get("/companies")
def get_companies(
    country: str = Query(None, description="Filter by country"),
    industry: str = Query(None, description="Filter by industry"),
    limit: int = Query(100, description="Max number of results to return"),
):
    #return clean company records w/ optional filters
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=pyscopg2.extras.RealDictCursor) as cur:
            # build query dinamically based on filters
            query = """
                SELECT id, company_name, country, city, industry,
                       company_size, employee_count, revenue_usd,
                       founded_year, website, linkedin_url,
                       is_public, data_quality_score
                FROM companies
                WHERE 1=1
            """
            params = []
            
            if country:
                query += " AND LOWER(country) = LOWER(%s)"
                params.append(country)

            if industry:
                query += " AND LOWER(industry) = LOWER(%s)"
                params.append(industry)

            query += " LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            results = cur.fetchall()

    finally:
        conn.close()

    return {"count": len(results), "data": results}
                
@app.get("/companies/{company_id}")
def get_company_by_id(company_id: int):
    #return one company by ID
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, company_name, country, city, industry,
                       company_size, employee_count, revenue_usd,
                       founded_year, website, linkedin_url,
                       is_public, data_quality_score
                FROM companies
                WHERE id = %s
            """, (company_id,))
            result = cur.fetchone()

    finally:
        conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Company not found")

    return result
