"""
Evaluasi akurasi sistem rekomendasi: Precision@5 dan Recall@5.

Menjawab tujuan penelitian, yaitu mengukur akurasi sistem dalam menghasilkan
rekomendasi resep yang relevan berdasarkan input bahan makanan pengguna.
Baseline TF-IDF dilaporkan berdampingan sebagai pembanding, bukan berdiri
sendiri.

Baseline menerima query mentah, sedangkan sistem melewati
split_known_ingredients() lebih dulu (normalisasi sinonim, koreksi typo,
gating bahan luar-domain). Jadi yang diukur adalah pipeline utuh, bukan
encoder-nya saja. Konsekuensinya: pada subset `sinonim`, ground truth memakai
nama bahan kanonik sementara baseline hanya melihat ejaan yang diketik,
sehingga skor baseline di subset itu rendah secara struktural. Ekspektasi
(TARGET_RATIO, pita GT, verdict meets_*) hanya berlaku untuk sistem; baseline
dilaporkan sebagai nilai terukur tanpa verdict.

Ground truth
------------
Resep relevan bila mengandung SEMUA bahan inti query (regex word-boundary,
mis. \\bayam\\b tidak cocok di dalam "bayam"). Bahan inti tidak termasuk bumbu
dasar (garam, kecap, lada, saos, kaldu, gula, minyak); cukup tidak
mencantumkannya di `keywords`. Alasannya: bumbu hampir universal di korpus
(garam di 12.284 dari 14.945 resep), dan sistem sendiri sudah memberi bobot
0.3-0.5 untuk bumbu vs 2.5-3.0 untuk bahan pokok. _VARIANTS membuat keyword
juga cocok dengan varian ejaannya (mis. "cabai" cocok dengan "cabe").

Test set: 20 query, subset `biasa` (15, ejaan baku) dan `sinonim` (5, satu
bahan ditulis dengan kata lain bermakna sama). Tiap query minimal 3 bahan
diketik dan minimal 2 bahan inti; dengan 1 bahan inti Precision@5 otomatis 1.0
dan berhenti membedakan metode.

Ekspektasi vs hasil (dideklarasikan sebelum diukur)
--------------------------------------------------
- expected_gt_min/max: pita +-20% di sekitar ukuran GT terukur. Ini cek
  integritas data (regex/dataset/kamus sinonim berubah), bukan performa metode.
- expected_precision_at_5 = TARGET_RATIO (0.80): satu ambang seragam untuk
  semua query, minimal 4 dari 5 hasil teratas relevan.
- expected_recall_at_5 = TARGET_RATIO * min(K, GT) / GT. Recall@5 tidak boleh
  diberi ambang tetap karena plafonnya ditentukan ukuran GT. Untuk GT >= K,
  recall@K = precision@K * K/GT, jadi verdict recall selalu sama dengan verdict
  precision; Recall@5 dilaporkan untuk nilai absolutnya, bukan sebagai uji
  kedua yang terpisah.

Jalur retrieval sama dengan produksi (split_known_ingredients lalu
engine.search), lihat routes/recommendations.py. Catatan untuk Bab IV: subset
`sinonim` menguji lapisan normalisasi leksikal (kamus SYNONYMS di
weighted_encoder), belum generalisasi semantik oleh Sentence Transformer.
"""

import asyncio
import logging
import re
import time
from typing import NamedTuple, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

from app.core.config import settings
from app.core.database import get_db
from app.services.recommendation_engine import engine
from app.services.weighted_encoder import SYNONYMS

# Balik kamus ejaan engine: kanonik -> semua ejaan yang dinormalisasi ke sana
# (termasuk dirinya). Supaya ground truth tahu "cabe" == "cabai".
_VARIANTS: dict[str, list[str]] = {}
for _variant, _canon in SYNONYMS.items():
    _VARIANTS.setdefault(_canon, [_canon])
    if _variant not in _VARIANTS[_canon]:
        _VARIANTS[_canon].append(_variant)

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])
logger = logging.getLogger(__name__)

K = 5   # Precision@K dan Recall@K dilaporkan pada K tunggal ini

# Fraksi skor yang harus dicapai tiap query. Untuk precision plafonnya 1.0 jadi
# ini langsung jadi ambang; untuk recall diskala plafon min(K, GT)/GT.
TARGET_RATIO = 0.80

CAT_PLAIN   = "biasa"
CAT_SYNONYM = "sinonim"

# Label verdict head-to-head. "Sistem", bukan "Sentence Transformer", karena yang
# dibandingkan dengan baseline adalah pipeline utuh (encoder + weighted encoding
# + query understanding), bukan encoder-nya saja.
LABEL_SYSTEM = "Sistem"
LABEL_TFIDF  = "TF-IDF"
LABEL_TIE    = "Seri"


class EvalQuery(NamedTuple):
    """Satu entri test set.

    `query` adalah yang diketik user (termasuk bumbu). `keywords` adalah bahan
    inti kanonik yang menentukan relevansi: tanpa bumbu, dan bahan bersinonim
    ditulis dalam bentuk kanoniknya.
    """
    query:           str
    keywords:        list[str]
    category:        str
    expected_gt_min: int
    expected_gt_max: int


# ── Test set ──────────────────────────────────────────────────────────────
# Ukuran GT diukur dari korpus; pita di bawah adalah +-20% dari hasil ukur itu.
# Semua entri tidak kosong (terukur 8-1089).

TEST_SET: list[EvalQuery] = [
    # 1 & 2: permintaan yang sama dalam ejaan baku dan sinonim; GT identik.
    EvalQuery("ikan, bawang merah, cabai",
              ["ikan", "bawang merah", "cabai"],                     CAT_PLAIN,   870, 1310),
    EvalQuery("seafood, bawang merah, cabe",
              ["ikan", "bawang merah", "cabai"],                     CAT_SYNONYM, 870, 1310),

    EvalQuery("tempe, kecap, cabai, garam, lada, daun salam",
              ["tempe", "cabai", "daun salam"],                      CAT_PLAIN,   320, 480),
    EvalQuery("tempe, tahu, tomat, lada, kecap",
              ["tempe", "tahu", "tomat"],                            CAT_PLAIN,    48, 74),
    EvalQuery("telur, bawang merah, bawang putih, tomat, cabai",
              ["telur", "bawang merah", "bawang putih", "tomat", "cabai"], CAT_PLAIN, 345, 520),
    EvalQuery("kecap, lada, daging sapi, bakso, kaldu",
              ["daging sapi", "bakso"],                              CAT_PLAIN,    26, 40),

    EvalQuery("telor, garam, kecap, saos, lada, tomat, cabai",
              ["telur", "tomat", "cabai"],                           CAT_SYNONYM, 450, 675),

    EvalQuery("tahu, bawang putih, kunyit",
              ["tahu", "bawang putih", "kunyit"],                    CAT_PLAIN,   230, 350),
    EvalQuery("daging, santan, kemiri, kunyit",
              ["daging", "santan", "kemiri", "kunyit"],              CAT_PLAIN,   230, 350),
    EvalQuery("daging, santan, garam, kecap, saos",
              ["daging", "santan"],                                  CAT_PLAIN,   465, 700),
    EvalQuery("ayam, kecap, kemiri",
              ["ayam", "kemiri"],                                    CAT_PLAIN,   595, 900),
    EvalQuery("ayam, kecap, saos, lada, tomat",
              ["ayam", "tomat"],                                     CAT_PLAIN,   680, 1025),

    EvalQuery("toge, kol, ayam",
              ["tauge", "kol", "ayam"],                              CAT_SYNONYM,  18, 28),
    EvalQuery("unggas, santan, kunyit, tomat, garam, kecap",
              ["ayam", "santan", "kunyit", "tomat"],                 CAT_SYNONYM,  28, 42),

    EvalQuery("ikan, kunyit, asam",
              ["ikan", "kunyit", "asam"],                            CAT_PLAIN,   105, 160),
    EvalQuery("lele, kunyit, garam, kecap, lengkuas, santan",
              ["lele", "kunyit", "lengkuas", "santan"],              CAT_PLAIN,     6, 10),
    EvalQuery("bayam, bawang putih, garam",
              ["bayam", "bawang putih"],                             CAT_PLAIN,    35, 53),

    EvalQuery("sayuran hijau, bawang putih, bawang merah, lada, garam, kecap",
              ["bayam", "bawang putih", "bawang merah"],             CAT_SYNONYM,  16, 26),

    EvalQuery("kangkung, bawang putih, terasi, garam, kecap",
              ["kangkung", "bawang putih", "terasi"],                CAT_PLAIN,    12, 20),
    EvalQuery("gurame, garam, kecap, saos, bawang putih",
              ["gurame", "bawang putih"],                            CAT_PLAIN,    76, 115),
]


# ── Retrieval ─────────────────────────────────────────────────────────────

async def _search(db: AsyncIOMotorDatabase, query: str, k: int) -> list[str]:
    """Retrieve lewat jalur produksi: query understanding lalu semantic search.

    Sama dengan routes/recommendations.py, termasuk normalisasi sinonim yang
    ada di split_known_ingredients(), bukan di search().
    """
    known, _ignored = engine.split_known_ingredients(query)
    if not known:
        return []
    results = await engine.search(db=db, query_text=known, top_n=k)
    return [r["recipe_id"] for r in results][:k]


# ── Baseline: TF-IDF ──────────────────────────────────────────────────────
# Dibangun sekali per proses dan di-cache; korpus tidak berubah saat runtime.

_tfidf_cache: Optional[dict] = None


def _build_tfidf_model(ids: list[str], texts: list[str]) -> dict:
    """Fit TF-IDF vectorizer di korpus resep.

    Bigram diikutkan supaya frasa seperti "bawang putih" jadi satu term, bukan
    dua unigram terpisah. min_df=2 buang term yang cuma muncul di satu resep,
    sublinear_tf meredam pengulangan.
    """
    vec = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )
    matrix = vec.fit_transform(texts)
    return {"ids": ids, "vectorizer": vec, "matrix": matrix}


def _search_tfidf(model: dict, query: str, k: int) -> list[str]:
    """Top-k recipe id by cosine similarity TF-IDF terhadap query MENTAH.

    Sengaja tidak lewat split_known_ingredients(): baseline adalah lexical
    retriever biasa tanpa lapisan query understanding. Itu sebabnya subset
    `sinonim` skornya mendekati nol di sini (baseline tak pernah lihat
    "seafood" jadi "ikan").
    """
    qvec = model["vectorizer"].transform([query])
    scores = sk_cosine(qvec, model["matrix"])[0]
    top_k = np.argsort(scores)[::-1][:k]
    return [model["ids"][int(i)] for i in top_k]


async def _get_or_build_tfidf(db: AsyncIOMotorDatabase) -> dict:
    global _tfidf_cache
    if _tfidf_cache is not None:
        return _tfidf_cache

    docs = await db["recipes"].find(
        {}, {"_id": 1, "ingredients_cleaned": 1}
    ).to_list(length=None)
    ids = [str(d["_id"]) for d in docs]
    texts = [d.get("ingredients_cleaned", "") for d in docs]

    _tfidf_cache = await asyncio.to_thread(_build_tfidf_model, ids, texts)
    logger.info(
        "TF-IDF baseline ready: %d docs, vocab_size=%d",
        len(ids), len(_tfidf_cache["vectorizer"].vocabulary_),
    )
    return _tfidf_cache


# ── Helpers ───────────────────────────────────────────────────────────────

def _kw_regex(kw: str) -> str:
    """Regex word-boundary yang cocok dengan keyword atau varian ejaannya."""
    variants = _VARIANTS.get(kw, [kw])
    return r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b"


async def _ground_truth_ids(db: AsyncIOMotorDatabase, keywords: list[str]) -> set[str]:
    """ID resep yang mengandung SEMUA keyword (varian ejaan apa pun) di ingredients_cleaned."""
    conditions = [
        {"ingredients_cleaned": {"$regex": _kw_regex(kw), "$options": "i"}}
        for kw in keywords
    ]
    mongo_q = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    docs = await db["recipes"].find(mongo_q, {"_id": 1}).to_list(length=None)
    return {str(d["_id"]) for d in docs}


def _precision(retrieved: list[str], relevant: set[str]) -> float:
    if not retrieved:
        return 0.0
    return sum(1 for r in retrieved if r in relevant) / len(retrieved)


def _recall(retrieved: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    return sum(1 for r in retrieved if r in relevant) / len(relevant)


def recall_ceiling(gt_size: int) -> float:
    """Recall@K maksimum yang mungkin dicapai query ini.

    Hanya K hasil dikembalikan, jadi paling banyak min(K, GT) resep GT bisa
    ketemu. Tanpa ini, GT besar akan tampak seperti kegagalan sistem padahal
    itu batas aritmetika.
    """
    if gt_size <= 0:
        return 0.0
    return min(K, gt_size) / gt_size


def expected_recall(gt_size: int) -> float:
    """Recall@K yang diharapkan: TARGET_RATIO dari nilai yang bisa dicapai.

    Dikembalikan dan dibandingkan tanpa pembulatan. Membulatkan ambang ke 4
    desimal bisa menaikkannya di atas nilai eksak untuk GT besar (GT=1089 ->
    0.0036730... jadi 0.0037), sehingga query yang tepat menyentuh target
    precision malah gagal di cek recall gara-gara pembulatan. Caller membulatkan
    hanya untuk tampilan.
    """
    return TARGET_RATIO * recall_ceiling(gt_size)


def _f1(p: float, r: float) -> float:
    return round(2 * p * r / (p + r), 4) if (p + r) > 0 else 0.0


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _summarise(scores: list[tuple[float, float]]) -> dict:
    """Rata-ratakan list pasangan (precision, recall) jadi satu blok ringkasan."""
    p = _avg([s[0] for s in scores])
    r = _avg([s[1] for s in scores])
    return {
        "n":                     len(scores),
        f"avg_precision_at_{K}": p,
        f"avg_recall_at_{K}":    r,
        "f1_macro":              _f1(p, r),
    }


def _winner(system_score: float, baseline_score: float) -> str:
    """Metode mana yang skornya lebih tinggi, atau LABEL_TIE kalau sama.

    Caller mengirim skor yang SUDAH dibulatkan supaya verdict konsisten dengan
    angka yang ditampilkan. Dua dari 20 query memang seri, jadi menghitung seri
    sebagai kemenangan sistem akan melebih-lebihkan hasil.
    """
    if system_score > baseline_score:
        return LABEL_SYSTEM
    if baseline_score > system_score:
        return LABEL_TFIDF
    return LABEL_TIE


def _query_row(
    entry: EvalQuery,
    gt_size: int,
    p: float,
    r: float,
    tp: float,
    tr: float,
) -> dict:
    """Bangun satu baris hasil per query.

    Menerima skor yang belum dibulatkan supaya caller bisa agregasi pada presisi
    penuh, sementara fungsi ini membulatkan hanya untuk tampilan. `tp`/`tr`
    adalah skor baseline: dilaporkan untuk perbandingan, tidak dipakai verdict.
    """
    exp_r = expected_recall(gt_size)
    # Bulatkan sebelum dibandingkan supaya verdict cocok dengan angka tampilan.
    p_shown, tp_shown = round(p, 4), round(tp, 4)
    return {
        "query":                      entry.query,
        "keywords":                   entry.keywords,
        "category":                   entry.category,
        # ekspektasi, dideklarasikan sebelum diukur, khusus sistem
        "expected_gt_min":            entry.expected_gt_min,
        "expected_gt_max":            entry.expected_gt_max,
        f"expected_precision_at_{K}": TARGET_RATIO,
        f"expected_recall_at_{K}":    round(exp_r, 4),
        f"recall_ceiling_at_{K}":     round(recall_ceiling(gt_size), 4),
        # terukur, sistem
        "ground_truth_size":          gt_size,
        f"precision_at_{K}":          p_shown,
        f"recall_at_{K}":             round(r, 4),
        # terukur, baseline TF-IDF: GT sama, tanpa target sendiri
        f"tfidf_precision_at_{K}":    tp_shown,
        f"tfidf_recall_at_{K}":       round(tr, 4),
        # head-to-head, berdasarkan Precision@K
        "winner":                     _winner(p_shown, tp_shown),
        # verdict
        "gt_within_expected":         entry.expected_gt_min <= gt_size <= entry.expected_gt_max,
        "meets_precision_target":     p >= TARGET_RATIO,
        "meets_recall_target":        r >= exp_r - 1e-9,
    }


# ── Endpoint ──────────────────────────────────────────────────────────────

@router.get(
    "/metrics",
    summary=f"Akurasi sistem rekomendasi: Precision@{K} & Recall@{K} pada 20 query, ekspektasi vs hasil",
)
async def get_metrics(db: AsyncIOMotorDatabase = Depends(get_db)):
    if not engine.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation engine belum siap",
        )

    t0 = time.perf_counter()

    tfidf_model = await _get_or_build_tfidf(db)

    all_gts, all_retrieved = await asyncio.gather(
        asyncio.gather(*[_ground_truth_ids(db, e.keywords) for e in TEST_SET]),
        asyncio.gather(*[_search(db, e.query, K) for e in TEST_SET]),
    )

    # Baseline memakai query mentah yang diketik, lihat _search_tfidf.
    all_tfidf: list[list[str]] = await asyncio.to_thread(
        lambda: [_search_tfidf(tfidf_model, e.query, K) for e in TEST_SET]
    )

    per_query: list[dict] = []
    scored: list[tuple[float, float]] = []
    tfidf_scored: list[tuple[float, float]] = []
    by_cat: dict[str, list[tuple[float, float]]] = {}
    by_cat_tfidf: dict[str, list[tuple[float, float]]] = {}

    for entry, gt_ids, retrieved, tf_retrieved in zip(
        TEST_SET, all_gts, all_retrieved, all_tfidf
    ):
        gt_size = len(gt_ids)
        p = _precision(retrieved, gt_ids)
        r = _recall(retrieved, gt_ids)
        tp = _precision(tf_retrieved, gt_ids)
        tr = _recall(tf_retrieved, gt_ids)

        if gt_ids:  # query tanpa ground truth tidak bisa dinilai
            scored.append((p, r))
            tfidf_scored.append((tp, tr))
            by_cat.setdefault(entry.category, []).append((p, r))
            by_cat_tfidf.setdefault(entry.category, []).append((tp, tr))

        per_query.append(_query_row(entry, gt_size, p, r, tp, tr))

    overall = _summarise(scored)
    baseline = _summarise(tfidf_scored)
    by_category = {c: _summarise(v) for c, v in by_cat.items()}
    for c, v in by_cat_tfidf.items():
        by_category[c]["tfidf"] = _summarise(v)
        by_category[c]["winner"] = _winner(
            by_category[c][f"avg_precision_at_{K}"],
            by_category[c]["tfidf"][f"avg_precision_at_{K}"],
        )

    return {
        "method":          f"Sentence Transformer ({settings.model_name}) + Weighted Encoding",
        "baseline_method": "TF-IDF (word 1-2gram, min_df=2, sublinear_tf), query mentah tanpa query understanding",
        "k":               K,
        "test_set_size":   len(TEST_SET),
        "valid_queries":   len(scored),
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "target_ratio":    TARGET_RATIO,
        f"target_precision_at_{K}": TARGET_RATIO,
        "queries_meeting_precision_target": sum(1 for q in per_query if q["meets_precision_target"]),
        "queries_meeting_recall_target":    sum(1 for q in per_query if q["meets_recall_target"]),
        "queries_meeting_both":             sum(
            1 for q in per_query
            if q["meets_precision_target"] and q["meets_recall_target"]
        ),
        "gt_within_expected_count":         sum(1 for q in per_query if q["gt_within_expected"]),
        f"avg_precision_at_{K}":            overall[f"avg_precision_at_{K}"],
        f"avg_recall_at_{K}":               overall[f"avg_recall_at_{K}"],
        f"avg_expected_recall_at_{K}":      _avg([q[f"expected_recall_at_{K}"] for q in per_query]),
        "f1_macro":       overall["f1_macro"],
        "baseline_tfidf": baseline,
        # Verdict head-to-head
        f"winner_by_precision_at_{K}": _winner(
            overall[f"avg_precision_at_{K}"], baseline[f"avg_precision_at_{K}"]
        ),
        "winner_by_f1_macro": _winner(overall["f1_macro"], baseline["f1_macro"]),
        f"precision_margin_at_{K}": round(
            overall[f"avg_precision_at_{K}"] - baseline[f"avg_precision_at_{K}"], 4
        ),
        "queries_system_wins": sum(1 for q in per_query if q["winner"] == LABEL_SYSTEM),
        "queries_tfidf_wins":  sum(1 for q in per_query if q["winner"] == LABEL_TFIDF),
        "queries_tie":         sum(1 for q in per_query if q["winner"] == LABEL_TIE),
        "by_category":    by_category,
        "per_query":      per_query,
    }
