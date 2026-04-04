# data-bridge-pipeline

End-to-end data pipeline: ingest from SFTP/S3, clean PII, and redistribute via API.

## Overview

This project replicates the core business of a data marketplace provider:

1. A data provider uploads a CSV file to an SFTP server (backed by AWS S3)
2. The pipeline detects new files, downloads them, and removes all PII and provider metadata
3. Clean data is loaded into PostgreSQL in batches
4. A FastAPI bridge exposes the clean data to clients via REST API

The provider identity is never exposed to the client.

## Architecture
Provider → SFTP (AWS Transfer Family) → S3
│
ingest_s3.py
(detects new files,
tracks via Postgres log)
│
clean_and_load.py
(removes PII + provider metadata,
validates, loads in batches)
│
Postgres
│
FastAPI (main.py)
│
Client

## Stack

- Python 3.12
- PostgreSQL 15 (Docker)
- AWS S3 + Transfer Family (SFTP)
- FastAPI + Uvicorn
- pandas, boto3, psycopg2

## Project Structure
bridge-pipeline/
├── api/
│   └── main.py              # FastAPI bridge endpoints
├── scripts/
│   ├── generate_fake_data.py  # generates realistic provider CSV with PII
│   ├── ingest_s3.py           # detects and downloads new S3 files
│   └── clean_and_load.py      # cleans PII, validates, loads to Postgres
├── data/
│   └── raw/                 # downloaded files land here
├── docker-compose.yml       # Postgres setup
├── requirements.txt
└── .env                     # credentials (not committed)

## Setup
```bash
# clone the repo
git clone https://github.com/LorenzoMinon/data-bridge-pipeline.git
cd data-bridge-pipeline

# create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# copy and fill in your credentials
cp .env.example .env

# start Postgres
docker compose up -d
```

## Running the Pipeline
```bash
# 1. generate fake provider data and upload to S3
python scripts/generate_fake_data.py
aws s3 cp data/raw/provider_export_v1.csv s3://your-bucket/public-folder/

# 2. ingest new files from S3
python scripts/ingest_s3.py

# 3. clean PII and load to Postgres
python scripts/clean_and_load.py

# 4. start the API
uvicorn api.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| GET | `/companies` | List clean company records |
| GET | `/companies/{id}` | Get a single company by ID |

### Filter examples
GET /companies?country=Argentina
GET /companies?industry=Technology
GET /companies?country=Brazil&industry=Finance&limit=50

## Key Design Decisions

**Idempotency**: The `ingested_files` log table ensures files are never processed twice. The `ON CONFLICT DO NOTHING` on insert prevents duplicate records even if the pipeline runs multiple times.

**PII removal**: All contact information and provider metadata is stripped before data reaches Postgres. The client API never exposes who the original data provider is.

**Batch loading**: Data is inserted in configurable batches (default 100 rows) with per-batch logging for visibility into large file processing.