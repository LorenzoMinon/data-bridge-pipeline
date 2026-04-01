# generate a realistic fake daataset simulating provider's raw exp.
# includes business data, pii, and provider metada. all to be cleaned!

import csv
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

ROW_COUNT = 1000

OUTPUT_FILE = "data/raw/provider_export_v1.csv"

INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Retail", "Manufacturing",
    "Education", "Real Estate", "Logistics", "Energy", "Media"
]

PROVIDER_SOURCES = ["web_scraping", "partnership", "public_records", "purchased_list"]

CONTACT_TITLES = ["CEO", "CTO", "CFO", "COO", "VP of Sales", "Head of Data", "Director of Operations"]

COMPANY_SIZES = ["small", "medium", "large"]

PROVIDER_NAMES = ["DataVault Inc", "GlobalLeads Co", "InfoBridge Ltd", "MarketData Pro"]


def generate_company_row(provider_name: str) -> dict:
    # Pick a random founding year and build a realistic revenue based on company size
    size = random.choice(COMPANY_SIZES)
    founded_year = random.randint(1980, 2022)

    if size == "small":
        employee_count = random.randint(1, 50)
        revenue_usd = random.randint(100_000, 2_000_000)
    elif size == "medium":
        employee_count = random.randint(51, 500)
        revenue_usd = random.randint(2_000_001, 50_000_000)
    else:
        employee_count = random.randint(501, 10_000)
        revenue_usd = random.randint(50_000_001, 1_000_000_000)

    # Provider ingestion date — sometime in the last 2 years
    ingestion_date = fake.date_between(start_date="-2y", end_date="today")

    company_name = fake.company()

    return {
        # --- Business data (redistributable) ---
        "company_name": company_name,
        "country": fake.country(),
        "city": fake.city(),
        "industry": random.choice(INDUSTRIES),
        "company_size": size,
        "employee_count": employee_count,
        "revenue_usd": revenue_usd,
        "founded_year": founded_year,
        "website": f"www.{company_name.lower().replace(' ', '').replace(',', '')}.com",
        "linkedin_url": f"linkedin.com/company/{company_name.lower().replace(' ', '-').replace(',', '')}",
        "is_public": random.choice([True, False]),
        "data_quality_score": random.randint(1, 100),

        # --- PII (to be removed before redistribution) ---
        "contact_name": fake.name(),
        "contact_title": random.choice(CONTACT_TITLES),
        "contact_email": fake.email(),
        "contact_phone": fake.phone_number(),
        "contact_linkedin": f"linkedin.com/in/{fake.user_name()}",

        # --- Provider metadata (to be removed before redistribution) ---
        "provider_name": provider_name,
        "provider_id": fake.uuid4(),
        "provider_source": random.choice(PROVIDER_SOURCES),
        "provider_ingestion_date": ingestion_date,
        "provider_notes": fake.sentence(nb_words=8),
    }
    
def generate_dataset(row_count: int = ROW_COUNT, output_file: str = OUTPUT_FILE):
    print(f"Generating {row_count} rows...")

    rows = []
    for _ in range(row_count):
        # Each row gets assigned to a random provider
        provider = random.choice(PROVIDER_NAMES)
        rows.append(generate_company_row(provider))

    # Write to CSV
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Dataset saved to {output_file} — {row_count} rows, {len(rows[0].keys())} columns")


if __name__ == "__main__":
    generate_dataset()