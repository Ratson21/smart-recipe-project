"""
Latency measurement: Sentence Transformer + WSIE search vs. TF-IDF baseline.

Purpose
-------
Measure per-query response time (not the one-time model/vector load at
startup) to support an efficiency claim in the paper.

Reuses `_search`, `_get_or_build_tfidf`, `_search_tfidf`, `TEST_SET`, `K`
directly from app.routes.evaluation (production code, unmodified) - so the
exact same retrieval path and query set used for the P@5/R@5 table is what
gets timed here. This script only measures; it does not import or write
anything under app/.

Methodology
-----------
1. engine.initialize(db) once (loads model + recipe_vectors.npy from disk -
   this is the one-time startup cost and is EXCLUDED from all timings below).
2. One warm-up call per method (first inference on a fresh model can include
   framework-level lazy-init/JIT/thread-pool warmup that is not
   representative of steady-state per-query cost) - discarded, not counted.
3. For each of the 20 TEST_SET queries, call the method 5 times in a row,
   wall-clock each call individually with time.perf_counter() immediately
   before/after the `await`/call - 100 timed calls per method.
4. Report mean / median / p95 / min / max in milliseconds.

`_search` is async (it awaits `engine.search`, which internally does
`asyncio.to_thread(...)` for the actual encode). Timing is taken around the
`await _search(...)` call itself, in a single already-running event loop
(one `asyncio.run` for the whole timed phase) - so what's measured is the
real wall-clock latency an API caller would experience (including the
to_thread dispatch), not event-loop start-up/teardown overhead from
repeatedly creating new loops.
"""

import asyncio
import json
import platform
import statistics
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_DIR))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.routes.evaluation import (  # noqa: E402
    K,
    TEST_SET,
    _get_or_build_tfidf,
    _search,
    _search_tfidf,
)
from app.services.recommendation_engine import engine  # noqa: E402

N_RUNS_PER_QUERY = 5


def _stats_ms(samples_s: list[float]) -> dict:
    ms = sorted(s * 1000 for s in samples_s)
    n = len(ms)
    p95_idx = min(n - 1, round(0.95 * (n - 1)))
    return {
        "n": n,
        "mean_ms": round(statistics.mean(ms), 3),
        "median_ms": round(statistics.median(ms), 3),
        "p95_ms": round(ms[p95_idx], 3),
        "min_ms": round(min(ms), 3),
        "max_ms": round(max(ms), 3),
    }


async def _time_search(db) -> tuple[dict, list[dict]]:
    # Warm-up (discarded) - first call can include lazy init not
    # representative of steady state.
    await _search(db, TEST_SET[0].query, K)

    per_query = []
    all_samples: list[float] = []
    for entry in TEST_SET:
        samples = []
        for _ in range(N_RUNS_PER_QUERY):
            t0 = time.perf_counter()
            await _search(db, entry.query, K)
            t1 = time.perf_counter()
            samples.append(t1 - t0)
        all_samples.extend(samples)
        per_query.append({"query": entry.query, **_stats_ms(samples)})
    return _stats_ms(all_samples), per_query


def _time_tfidf(model: dict) -> tuple[dict, list[dict]]:
    _search_tfidf(model, TEST_SET[0].query, K)  # warm-up, discarded

    per_query = []
    all_samples: list[float] = []
    for entry in TEST_SET:
        samples = []
        for _ in range(N_RUNS_PER_QUERY):
            t0 = time.perf_counter()
            _search_tfidf(model, entry.query, K)
            t1 = time.perf_counter()
            samples.append(t1 - t0)
        all_samples.extend(samples)
        per_query.append({"query": entry.query, **_stats_ms(samples)})
    return _stats_ms(all_samples), per_query


def _machine_spec() -> dict:
    spec = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python_version": platform.python_version(),
    }
    try:
        import torch
        spec["torch_version"] = torch.__version__
        spec["cuda_available"] = torch.cuda.is_available()
        spec["mps_available"] = torch.backends.mps.is_available()
    except Exception:
        pass
    return spec


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]

    n_docs = await db["recipes"].count_documents({})
    print(f"Mongo: {n_docs} recipes in {settings.database_name!r}")

    print("\n== Initialising engine (model + recipe_vectors.npy load - excluded from timing) ==")
    t0 = time.perf_counter()
    await engine.initialize(db)
    startup_s = time.perf_counter() - t0
    print(f"Engine ready in {startup_s:.2f}s ({len(engine.recipe_ids)} vectors) "
          f"- model device: {engine.model.device}")

    print("\n== Building TF-IDF baseline model (excluded from timing) ==")
    t0 = time.perf_counter()
    tfidf_model = await _get_or_build_tfidf(db)
    print(f"TF-IDF ready in {time.perf_counter() - t0:.2f}s")

    print(f"\n== Timing {len(TEST_SET)} queries x {N_RUNS_PER_QUERY} runs, "
          f"both methods (1 warm-up call each, discarded) ==")

    st_overall, st_per_query = await _time_search(db)
    tfidf_overall, tfidf_per_query = _time_tfidf(tfidf_model)

    spec = _machine_spec()

    # ── Print summary table ─────────────────────────────────────────────
    header = f"{'Metode':<32} {'Mean (ms)':>10} {'Median (ms)':>12} {'P95 (ms)':>10} {'Min (ms)':>10} {'Max (ms)':>10}"
    print("\n" + header)
    print("-" * len(header))
    for label, s in [
        ("Sentence Transformer + WSIE", st_overall),
        ("TF-IDF (Baseline)", tfidf_overall),
    ]:
        print(f"{label:<32} {s['mean_ms']:>10.3f} {s['median_ms']:>12.3f} "
              f"{s['p95_ms']:>10.3f} {s['min_ms']:>10.3f} {s['max_ms']:>10.3f}")
    print("-" * len(header))
    print(f"\nn = {st_overall['n']} measurements per method ({len(TEST_SET)} query x {N_RUNS_PER_QUERY} run)")

    print("\n== Machine spec ==")
    for k, v in spec.items():
        print(f"  {k}: {v}")

    out = {
        "k": K,
        "n_queries": len(TEST_SET),
        "runs_per_query": N_RUNS_PER_QUERY,
        "engine_startup_seconds_excluded": round(startup_s, 3),
        "machine_spec": spec,
        "sentence_transformer_wsie": {"overall": st_overall, "per_query": st_per_query},
        "tfidf_baseline": {"overall": tfidf_overall, "per_query": tfidf_per_query},
    }
    out_path = Path(__file__).resolve().parent / "latency_results.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results -> {out_path}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
