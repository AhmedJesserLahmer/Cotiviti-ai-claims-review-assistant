"""Loads the generated CSVs in backend/data/ into MongoDB collections.

Run with: python -m data_gen.seed_mongo
"""

import asyncio
import os

import pandas as pd

from db.mongo import db

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

COLLECTIONS = {
    "providers.csv": "providers",
    "patients.csv": "patients",
    "claims.csv": "claims",
    "provider_timeseries.csv": "provider_timeseries",
}


async def seed():
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
    asyncio.run(seed())
