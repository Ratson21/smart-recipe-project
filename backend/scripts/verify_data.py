"""
verify_data.py - Verifikasi kualitas data recipes di MongoDB.
Usage: python scripts/verify_data.py
"""

import os, sys
from pymongo import MongoClient
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MONGODB_URL   = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "smart_recipe_db")

REQUIRED_FIELDS = [
    "title", "ingredients_raw", "ingredients_cleaned", "steps",
    "category", "total_ingredients", "total_steps",
    "estimated_time_minutes", "difficulty_level",
    "average_rating", "total_reviews",
]

SAMPLE_FIELDS = {
    "title": 1, "total_ingredients": 1, "difficulty_level": 1,
    "estimated_time_minutes": 1, "category": 1,
}


def fmt_bar(value: float, total: float, width: int = 20) -> str:
    filled = round(value / total * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def check_nulls(doc: dict) -> list[str]:
    """Return list of required fields that are null/empty/missing."""
    bad = []
    for field in REQUIRED_FIELDS:
        val = doc.get(field)
        if val is None or val == "" or val == []:
            bad.append(field)
    return bad


def main():
    client = MongoClient(MONGODB_URL)
    col    = client[DATABASE_NAME]["recipes"]

    total_docs = col.count_documents({})
    print(f"{'='*60}")
    print(f"  VERIFIKASI DATA - smart_recipe_db.recipes")
    print(f"{'='*60}")
    print(f"  Total dokumen : {total_docs:,}\n")

    # ── 1. Sample 20 resep random ────────────────────────────────────────
    sample = list(col.aggregate([
        {"$sample": {"size": 20}},
        {"$project": {**SAMPLE_FIELDS, "_id": 0}},
    ]))

    print(f"{'─'*60}")
    print(f"  {'TITLE':<35} {'ING':>4} {'DIFF':<8}")
    print(f"{'─'*60}")
    for doc in sample:
        title   = doc.get("title", "?")[:34]
        ing     = doc.get("total_ingredients", 0)
        diff    = doc.get("difficulty_level", "?")
        flag    = "  ✓" if all([title, ing, diff]) else "  ✗"
        print(f"  {title:<35} {ing:>4} {diff:<8}{flag}")
    print(f"{'─'*60}\n")

    # ── 2. Null / missing field check pada seluruh collection ────────────
    print(f"  Null-check field wajib (seluruh {total_docs:,} dokumen)...")
    null_counts: dict[str, int] = {f: 0 for f in REQUIRED_FIELDS}

    cursor = col.find({}, {f: 1 for f in REQUIRED_FIELDS})
    for doc in cursor:
        for field in check_nulls(doc):
            null_counts[field] += 1

    any_issue = False
    for field, count in null_counts.items():
        if count > 0:
            any_issue = True
            pct = count / total_docs * 100
            print(f"  ✗  {field:<30} {count:>6,} dokumen ({pct:.1f}%) bermasalah")
    if not any_issue:
        print(f"  ✓  Semua field wajib terisi di seluruh dokumen\n")
    else:
        print()

    # ── 3. Summary statistik ─────────────────────────────────────────────
    agg = list(col.aggregate([{"$group": {
        "_id": None,
        "avg_ing":      {"$avg": "$total_ingredients"},
        "avg_time":     {"$avg": "$estimated_time_minutes"},
        "total_rating": {"$sum": "$total_reviews"},
    }}]))[0]

    print(f"  {'─'*40}")
    print(f"  SUMMARY STATISTIK")
    print(f"  {'─'*40}")
    print(f"  Rata-rata bahan/resep   : {agg['avg_ing']:>8.1f}")
    print(f"  Rata-rata waktu masak   : {agg['avg_time']:>8.1f} menit")
    print(f"  Total ulasan            : {agg['total_rating']:>8,}")

    # ── 4. Distribusi difficulty ─────────────────────────────────────────
    print(f"\n  Distribusi Difficulty Level:")
    diff_pipeline = [
        {"$group": {"_id": "$difficulty_level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    diff_data = list(col.aggregate(diff_pipeline))
    for d in diff_data:
        label = d["_id"] or "(null)"
        count = d["count"]
        bar   = fmt_bar(count, total_docs)
        pct   = count / total_docs * 100
        print(f"  {label:<8} {bar} {count:>6,} ({pct:.1f}%)")

    print(f"\n{'='*60}")
    status = "LULUS ✓" if not any_issue else "ADA MASALAH ✗"
    print(f"  STATUS VERIFIKASI: {status}")
    print(f"{'='*60}\n")

    client.close()
    sys.exit(1 if any_issue else 0)


if __name__ == "__main__":
    main()
