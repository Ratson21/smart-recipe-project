"""
ETL script: load Indonesian_Food_Recipes.csv ke MongoDB collection 'recipes'.
Jalankan dari root backend/:
    python scripts/etl_recipes.py
"""

import os
import sys
import random
import pandas as pd
from pymongo import MongoClient, InsertOne
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MONGODB_URL   = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "smart_recipe_db")
CSV_PATH      = os.path.join(BASE_DIR, "data", "Indonesian_Food_Recipes.csv")

BATCH_SIZE = 500


def difficulty(total_ingredients: int) -> str:
    if total_ingredients < 5:
        return "Mudah"
    if total_ingredients <= 10:
        return "Sedang"
    return "Sulit"


def build_doc(row) -> dict:
    total_ing = int(row["Total Ingredients"])
    return {
        "title":               str(row["Title"]).strip(),
        "ingredients_raw":     str(row["Ingredients"]).strip(),
        "ingredients_cleaned": str(row["Ingredients Cleaned"]).strip(),
        "steps":               str(row["Steps"]).strip(),
        "category":            str(row["Category"]).strip(),
        "total_ingredients":   total_ing,
        "total_steps":         int(row["Total Steps"]),
        "estimated_time_minutes": random.randint(15, 120),
        "difficulty_level":    difficulty(total_ing),
        "average_rating":      0.0,
        "total_reviews":       0,
    }


def main():
    print(f"Membaca CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"Total baris CSV: {len(df):,}")

    client     = MongoClient(MONGODB_URL)
    db         = client[DATABASE_NAME]
    collection = db["recipes"]

    existing = collection.count_documents({})
    if existing > 0:
        print(f"Collection sudah berisi {existing:,} dokumen - drop & re-insert.")
        collection.drop()

    total    = len(df)
    inserted = 0

    for start in range(0, total, BATCH_SIZE):
        batch = df.iloc[start : start + BATCH_SIZE]
        ops   = [InsertOne(build_doc(row)) for _, row in batch.iterrows()]
        result = collection.bulk_write(ops, ordered=False)
        inserted += result.inserted_count
        pct = inserted / total * 100
        print(f"  inserted {inserted:,}/{total:,} ({pct:.1f}%)", end="\r", flush=True)

    print()  # newline after progress line

    # ── Indexes ────────────────────────────────────────────────────────────
    collection.create_index("title")
    collection.create_index("category")
    collection.create_index("difficulty_level")
    collection.create_index([("average_rating", -1)])
    print("Index dibuat: title, category, difficulty_level, average_rating")

    final_count = collection.count_documents({})
    print(f"\nVerifikasi - total dokumen di collection 'recipes': {final_count:,}")

    if final_count != total:
        print(f"PERINGATAN: jumlah tidak cocok! CSV={total}, DB={final_count}", file=sys.stderr)
        sys.exit(1)

    print("ETL selesai.")
    client.close()


if __name__ == "__main__":
    main()
