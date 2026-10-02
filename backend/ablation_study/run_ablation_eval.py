"""
Ablation study: WSIE (Weighted Semantic Ingredient Encoding) vs. uniform
weighting (ablation), on the same 20-query test set used for Table 3.3.

What this script does
----------------------
1. Reuses TEST_SET, _ground_truth_ids(), _precision(), _recall() verbatim
   from app.routes.evaluation (the production evaluation module) - so the
   ground truth (word-boundary regex over ingredients_cleaned) and the 20
   queries are IDENTICAL to what produced the original WSIE numbers. No new
   queries are introduced here.
2. Initialises the PRODUCTION engine (app.services.recommendation_engine.engine,
   weighted by INGREDIENT_WEIGHTS) and the ABLATION engine
   (recommendation_engine_ablation.ablation_engine, uniform weight 1.0),
   each building/loading its own vector cache:
     - production: backend/data/recipe_vectors.npy + recipe_ids.json
     - ablation:   backend/data/recipe_vectors_ablation.npy + recipe_ids_ablation.json
   Neither run touches the other's cache file.
3. Runs both engines' full retrieval pipeline (split_known_ingredients then
   search) against the same 20 queries, scores Precision@5 / Recall@5 against
   the same ground truth, and prints a side-by-side per-query table.

This script and the modules it imports from ablation_study/ are
evaluation-only. Nothing under app/ is modified.

Run from backend/ with the ablation venv active:
    python ablation_study/run_ablation_eval.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ABLATION_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))   # for `app.*`
sys.path.insert(0, str(_ABLATION_DIR))  # for `recommendation_engine_ablation`, `weighted_encoder_ablation`

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.routes.evaluation import (  # noqa: E402
    TEST_SET,
    K,
    _ground_truth_ids,
    _precision,
    _recall,
)
from app.services.recommendation_engine import engine as wsie_engine  # noqa: E402
from recommendation_engine_ablation import ablation_engine  # noqa: E402


async def _search_with(engine_obj, db, query_text: str, k: int) -> list[str]:
    """Same retrieval path as app.routes.evaluation._search, parametrised by engine."""
    known, _ignored = engine_obj.split_known_ingredients(query_text)
    if not known:
        return []
    results = await engine_obj.search(db=db, query_text=known, top_n=k)
    return [r["recipe_id"] for r in results][:k]


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]

    n_docs = await db["recipes"].count_documents({})
    print(f"Mongo: {n_docs} recipes in {settings.database_name!r}")

    print("\n== Initialising WSIE (production) engine ==")
    t0 = time.perf_counter()
    await wsie_engine.initialize(db)
    print(f"WSIE engine ready in {time.perf_counter() - t0:.1f}s "
          f"({len(wsie_engine.recipe_ids)} vectors)")

    print("\n== Initialising ablation (uniform-weight) engine ==")
    t0 = time.perf_counter()
    await ablation_engine.initialize(db)
    print(f"Ablation engine ready in {time.perf_counter() - t0:.1f}s "
          f"({len(ablation_engine.recipe_ids)} vectors)")

    print(f"\n== Running {len(TEST_SET)} queries against both engines ==")
    rows = []
    wsie_scores, abl_scores = [], []

    for i, entry in enumerate(TEST_SET, start=1):
        gt_ids = await _ground_truth_ids(db, entry.keywords)

        wsie_retrieved = await _search_with(wsie_engine, db, entry.query, K)
        abl_retrieved = await _search_with(ablation_engine, db, entry.query, K)

        wp, wr = _precision(wsie_retrieved, gt_ids), _recall(wsie_retrieved, gt_ids)
        ap, ar = _precision(abl_retrieved, gt_ids), _recall(abl_retrieved, gt_ids)

        if gt_ids:  # queries with empty GT are excluded from averages, same as production
            wsie_scores.append((wp, wr))
            abl_scores.append((ap, ar))

        rows.append({
            "no": i,
            "query": entry.query,
            "category": entry.category,
            "gt_size": len(gt_ids),
            "p5_wsie": round(wp, 4),
            "p5_ablation": round(ap, 4),
            "r5_wsie": round(wr, 4),
            "r5_ablation": round(ar, 4),
        })

    def _avg(vals):
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    avg_p_wsie = _avg([s[0] for s in wsie_scores])
    avg_r_wsie = _avg([s[1] for s in wsie_scores])
    avg_p_abl = _avg([s[0] for s in abl_scores])
    avg_r_abl = _avg([s[1] for s in abl_scores])

    # Print table
    header = f"{'No':<3} {'Query':<55} {'P@5 WSIE':>9} {'P@5 Abl':>9} {'R@5 WSIE':>9} {'R@5 Abl':>9}"
    print("\n" + header)
    print("-" * len(header))
    for r in rows:
        q = r["query"] if len(r["query"]) <= 55 else r["query"][:52] + "..."
        print(f"{r['no']:<3} {q:<55} {r['p5_wsie']:>9.4f} {r['p5_ablation']:>9.4f} "
              f"{r['r5_wsie']:>9.4f} {r['r5_ablation']:>9.4f}")
    print("-" * len(header))
    print(f"{'':<3} {'AVERAGE (measured this run)':<55} {avg_p_wsie:>9.4f} {avg_p_abl:>9.4f} "
          f"{avg_r_wsie:>9.4f} {avg_r_abl:>9.4f}")
    print(f"{'':<3} {'Original WSIE reported (skripsi Table 3.3)':<55} {0.96:>9.4f} {'':>9} "
          f"{0.087:>9.4f} {'':>9}")

    # Save results
    out = {
        "k": K,
        "n_queries": len(TEST_SET),
        "n_valid_queries": len(wsie_scores),
        "avg_precision_at_5_wsie_measured": avg_p_wsie,
        "avg_recall_at_5_wsie_measured": avg_r_wsie,
        "avg_precision_at_5_ablation": avg_p_abl,
        "avg_recall_at_5_ablation": avg_r_abl,
        "avg_precision_at_5_wsie_reported_skripsi": 0.96,
        "avg_recall_at_5_wsie_reported_skripsi": 0.087,
        "per_query": rows,
    }
    out_path = _ABLATION_DIR / "ablation_results.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results -> {out_path}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
