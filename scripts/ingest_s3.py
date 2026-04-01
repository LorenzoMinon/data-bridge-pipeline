# ingest_s3.py
# connects to S3, detects new files, downloads them locally,
# and tracks processed files in a Postgres log table.

import os
import boto3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# AWS config
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "public-folder/")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Postgres config
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_DB = os.getenv("PG_DB", "pipeline_db")
PG_USER = os.getenv("PG_USER", "pipeline_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "pipeline_pass")

# Local folder where downloaded files land
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

def get_db_connection():
    """Open and return a Postgres connection."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def ensure_log_table(conn):
    """Create the ingestion log table if it doesn't exist yet."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ingested_files (
                id          SERIAL PRIMARY KEY,
                file_key    TEXT NOT NULL UNIQUE,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
    conn.commit()


def get_ingested_files(conn) -> set:
    """Return a set of file keys already recorded in the log."""
    with conn.cursor() as cur:
        cur.execute("SELECT file_key FROM ingested_files;")
        rows = cur.fetchall()
    return {row[0] for row in rows}


def mark_file_as_ingested(conn, file_key: str):
    """Record a file key in the log after successful download."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ingested_files (file_key) VALUES (%s) ON CONFLICT DO NOTHING;",
            (file_key,)
        )
    conn.commit()
    
def list_s3_files(bucket: str, prefix: str) -> list:
    """List all files in the S3 bucket under the given prefix."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

    files = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        # skip the folder itself, we only want actual files
        if not key.endswith("/"):
            files.append(key)

    return files


def download_file(bucket: str, file_key: str, destination_dir: str) -> str:
    """Download a single file from S3 to the local destination folder."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    filename = os.path.basename(file_key)
    local_path = os.path.join(destination_dir, filename)

    print(f"  Downloading: {file_key}")
    s3.download_file(bucket, file_key, local_path)
    print(f"  Saved to: {local_path}")

    return local_path


def run_ingestion():
    """Main ingestion function — detect new files in S3 and download them."""
    print("Starting S3 ingestion...")

    conn = get_db_connection()
    ensure_log_table(conn)

    # get files already processed
    already_ingested = get_ingested_files(conn)
    print(f"Files already ingested: {len(already_ingested)}")

    # list all files currently in S3
    s3_files = list_s3_files(S3_BUCKET, S3_PREFIX)
    print(f"Files found in S3: {len(s3_files)}")

    # figure out which ones are new
    new_files = [f for f in s3_files if f not in already_ingested]
    print(f"New files to process: {len(new_files)}")

    if not new_files:
        print("Nothing to do. All files already ingested.")
        conn.close()
        return

    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    for file_key in new_files:
        download_file(S3_BUCKET, file_key, RAW_DATA_DIR)
        mark_file_as_ingested(conn, file_key)
        print(f"  Logged: {file_key}")

    print(f"\nDone. {len(new_files)} file(s) ingested.")
    conn.close()


if __name__ == "__main__":
    run_ingestion()