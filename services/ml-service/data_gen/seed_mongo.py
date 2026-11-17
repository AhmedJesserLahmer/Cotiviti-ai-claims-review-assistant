"""Loads the generated CSVs in backend/data/ into MongoDB collections.

Run with: python -m data_gen.seed_mongo [--if-empty]

Without a flag it is a full reset: it replaces every seeded collection and deletes stored
analyses. ``--if-empty`` (used at container start) leaves a database that already holds
claims untouched, so restarting ml-service no longer wipes uploaded claims and analyses.
"""

import asyncio
import os
import sys

import pandas as pd

from db.mongo import db

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

COLLECTIONS = {
    "providers.csv": "providers",
    "patients.csv": "patients",
    "claims.csv": "claims",
    "provider_timeseries.csv": "provider_timeseries",
}


async def seed(only_if_empty: bool = False) -> dict[str, int]:
    if only_if_empty and await db["claims"].estimated_document_count() > 0:
        print("MongoDB already holds claims; skipping seed.")
        return {}

    counts = {}
    for filename, collection_name in COLLECTIONS.items():
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path)
        records = df.to_dict(orient="records")

        collection = db[collection_name]
        await collection.delete_many({})
        if records:
            await collection.insert_many(records)
        counts[collection_name] = len(records)

    await db["claim_analyses"].delete_many({})

    print("Seeded MongoDB collections:", counts)
    return counts


if __name__ == "__main__":
    asyncio.run(seed(only_if_empty="--if-empty" in sys.argv[1:]))
