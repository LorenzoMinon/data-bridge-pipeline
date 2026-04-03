# reads the raw provider csv, removes pii and metadata
# validates the data, and loads clean records into postgres in batches

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_DB = os.getenv("PG_DB", "pipeline_db")
PG_USER = os.getenv("PG_USER", "pipeline_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "pipeline_pass")

PII_COLUMNS = [
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_phone",
    "contact_linkedin",
]

PROVIDER_COLUMNS = [
    "provider_name",
    "provider_id",
    "provider_source",
    "provider_ingestion_date",
    "provider_notes",
]

# columns that must not be null
REQUIRED_COLUMNS = [
    "company_name",
    "country",
    "industry",
    "company_size",
]

BATCH_SIZE = 100


def get_db_connection():
    """Open and return a Postgres connection."""
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )


def ensure_companies_table(conn):
    # creates company table if it doesn't exist yet
    with conn.cursor() as cur:
        cur.execute(
            """
                CREATE TABLE IF NOT EXISTS companies (
                    id              SERIAL PRIMARY KEY,
                    company_name    TEXT NOT NULL,
                    country         TEXT,
                    city            TEXT,
                    industry        TEXT,
                    company_size    TEXT,
                    employee_count  INTEGER,
                    revenue_usd     BIGINT,
                    founded_year    INTEGER,
                    website         TEXT,
                    linkedin_url    TEXT,
                    is_public       BOOLEAN,
                    data_quality_score INTEGER,
                    source_file     TEXT,
                    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
                    
        """)
    conn.commit()
    
def clean_dataframe(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """Remove PII and provider metadata, validate, and prep for loading."""
    initial_rows = len(df)
    print(f"  Rows received: {initial_rows}")
    
    # drop PII and provider metadata !!!!!!!!
    columns_to_drop = PII_COLUMNS + PROVIDER_COLUMNS
    df = df.drop(columns=columns_to_drop, errors="ignore")
    print(f"  Removed columns: {columns_to_drop}")
    
    # drop rows where req columns are null
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped = initial_rows - len(df)
    if dropped > 0:
        print(f"  Dropped {dropped} rows with nulls in required columns")
        
    # normalize text columns
    text_columns = ["company_name", "country", "city", "industry", "company_size"]
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].str.strip()    
    
    # for tracking
    df["source_file"] = source_file

    print(f"  Rows after cleaning: {len(df)}")
    return df

def validate_dataframe(df: pd.DataFrame) -> bool:
    """Run basic validation checks before loading."""
    if len(df) == 0:
        print("  Validation failed: no rows to load")
        return False

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            print(f"  Validation failed: missing column '{col}'")
            return False

    print(f"  Validation passed — {len(df)} rows ready to load")
    return True


# load to postgres in batches ! 

def load_to_postgres(conn, df: pd.DataFrame):
    """Load cleaned dataframe into Postgres in batches."""
    records = df.to_dict(orient="records")
    total = len(records)
    loaded = 0

    with conn.cursor() as cur:
        for i in range(0, total, BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]

            execute_batch(cur, """
                INSERT INTO companies (
                    company_name, country, city, industry, company_size,
                    employee_count, revenue_usd, founded_year, website,
                    linkedin_url, is_public, data_quality_score, source_file
                ) VALUES (
                    %(company_name)s, %(country)s, %(city)s, %(industry)s,
                    %(company_size)s, %(employee_count)s, %(revenue_usd)s,
                    %(founded_year)s, %(website)s, %(linkedin_url)s,
                    %(is_public)s, %(data_quality_score)s, %(source_file)s
                )
                ON CONFLICT DO NOTHING;
            """, batch)

            loaded += len(batch)
            print(f"  Loaded batch: {loaded}/{total} rows")

    conn.commit()
    print(f"  Done — {loaded} rows committed to Postgres")
    

def run_cleaning(input_file: str):
    """Main function — clean and load a single provider CSV file."""
    print(f"\nProcessing: {input_file}")

    # read the raw CSV
    df = pd.read_csv(input_file)
    source_file = os.path.basename(input_file)

    # clean and validate
    df = clean_dataframe(df, source_file)
    if not validate_dataframe(df):
        print("  Aborting load due to validation failure.")
        return

    # load to Postgres
    conn = get_db_connection()
    ensure_companies_table(conn)
    load_to_postgres(conn, df)
    conn.close()

    print(f"Pipeline complete for: {source_file}")


if __name__ == "__main__":
    # process all CSV files in data/raw/
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

    csv_files = [
        os.path.join(raw_dir, f)
        for f in os.listdir(raw_dir)
        if f.endswith(".csv")
    ]

    if not csv_files:
        print("No CSV files found in data/raw/")
    else:
        for csv_file in csv_files:
            run_cleaning(csv_file)