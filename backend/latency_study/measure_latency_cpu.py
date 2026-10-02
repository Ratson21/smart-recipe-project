"""
Same latency measurement as measure_latency.py, but forces the
SentenceTransformer model onto CPU instead of auto-selecting Apple's MPS
(GPU) backend.

Why a separate script instead of a flag on measure_latency.py: forcing CPU
requires overriding how app.services.recommendation_engine constructs the
model (it calls plain `SentenceTransformer(settings.model_name)` with no
device argument, so it auto-picks MPS whenever available). Rather than
touch that production file, this script monkeypatches the
`SentenceTransformer` name INSIDE THE ALREADY-IMPORTED recommendation_engine
module object, at runtime, in this standalone process only - the file on
disk is never modified. `_load_model()` looks up `SentenceTransformer` as a
bare global at call time, so rebinding the module attribute before
`engine.initialize()` runs is enough to make it build the model with
device='cpu'.

Reuses all the timing helpers (_stats_ms, _time_search, _time_tfidf,
_machine_spec, N_RUNS_PER_QUERY) from measure_latency.py so the two runs are
identical except for the device.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_LATENCY_STUDY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))        # for `app.*`
sys.path.insert(0, str(_LATENCY_STUDY_DIR))  # for `measure_latency`

from sentence_transformers import SentenceTransformer as _RealSentenceTransformer  # noqa: E402

import app.services.recommendation_engine as _rec_engine_module  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.routes.evaluation import _get_or_build_tfidf  # noqa: E402
from app.services.recommendation_engine import engine  # noqa: E402
from measure_latency import N_RUNS_PER_QUERY, _machine_spec, _stats_ms, _time_search, _time_tfidf  # noqa: E402

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


def _cpu_sentence_transformer(model_name_or_path, *args, **kwargs):
    kwargs["device"] = "cpu"
    return _RealSentenceTransformer(model_name_or_path, *args, **kwargs)


# Runtime-only override, this process's import of the module object - does
# not touch app/services/recommendation_engine.py on disk.
_rec_engine_module.SentenceTransformer = _cpu_sentence_transformer


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]

    n_docs = await db["recipes"].count_documents({})
    print(f"Mongo: {n_docs} recipes in {settings.database_name!r}")

    print("\n== Initialising engine forced to CPU (excluded from timing) ==")
    t0 = time.perf_counter()
    await engine.initialize(db)
    startup_s = time.perf_counter() - t0
    print(f"Engine ready in {startup_s:.2f}s ({len(engine.recipe_ids)} vectors) "
          f"- model device: {engine.model.device}")
    assert str(engine.model.device) == "cpu", "CPU override did not take effect"

    print("\n== Building TF-IDF baseline model (excluded from timing) ==")
    t0 = time.perf_counter()
    tfidf_model = await _get_or_build_tfidf(db)
    print(f"TF-IDF ready in {time.perf_counter() - t0:.2f}s")

    from app.routes.evaluation import K, TEST_SET
    print(f"\n== Timing {len(TEST_SET)} queries x {N_RUNS_PER_QUERY} runs, "
          f"both methods (1 warm-up call each, discarded), CPU-only ==")

    st_overall, st_per_query = await _time_search(db)
    tfidf_overall, tfidf_per_query = _time_tfidf(tfidf_model)

    spec = _machine_spec()
    spec["forced_device"] = "cpu"

    header = f"{'Metode':<32} {'Mean (ms)':>10} {'Median (ms)':>12} {'P95 (ms)':>10} {'Min (ms)':>10} {'Max (ms)':>10}"
    print("\n" + header)
    print("-" * len(header))
    for label, s in [
        ("Sentence Transformer + WSIE (CPU)", st_overall),
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
        "sentence_transformer_wsie_cpu": {"overall": st_overall, "per_query": st_per_query},
        "tfidf_baseline": {"overall": tfidf_overall, "per_query": tfidf_per_query},
    }
    out_path = Path(__file__).resolve().parent / "latency_results_cpu.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results -> {out_path}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
