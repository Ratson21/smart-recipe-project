"""
Test integritas untuk test set evaluasi.

Angka evaluasi hanya berarti kalau TEST_SET memenuhi beberapa invariant yang
gampang rusak saat diedit manual:

  * bumbu tidak pernah bocor ke `keywords` (kalau bocor, relevansi jadi menguji
    cara membumbui, bukan hidangannya, dan GT mengecil drastis)
  * query sinonim memakai keyword kanonik, bukan ejaan yang diketik
  * pita ekspektasi valid dan target precision seragam

Murni unit test: tanpa model, tanpa database.
"""

import pytest

from app.routes.evaluation import (
    CAT_PLAIN,
    CAT_SYNONYM,
    K,
    TARGET_RATIO,
    TEST_SET,
    _f1,
    _precision,
    _recall,
    _summarise,
    expected_recall,
    recall_ceiling,
)

# Bumbu dasar yang sengaja dikeluarkan dari relevansi. Tetap ada di query yang
# diketik, tidak pernah di `keywords`.
SEASONINGS = {"garam", "kecap", "saos", "saus", "kaldu", "lada", "merica",
              "gula", "minyak", "penyedap"}

# Ejaan yang dinormalisasi engine; ground truth harus pakai bentuk kanonik.
NON_CANONICAL = {"seafood", "cabe", "telor", "toge", "taoge", "unggas",
                 "santen", "trasi", "terung", "wartel", "lombok",
                 "sayuran hijau", "sayur hijau"}


# ── Bentuk test set ───────────────────────────────────────────────────────

def test_test_set_has_expected_subset_sizes():
    counts = {c: sum(1 for e in TEST_SET if e.category == c)
              for c in (CAT_PLAIN, CAT_SYNONYM)}
    assert counts == {CAT_PLAIN: 15, CAT_SYNONYM: 5}
    assert len(TEST_SET) == 20


def test_queries_are_unique():
    queries = [e.query for e in TEST_SET]
    assert len(queries) == len(set(queries))


def test_every_category_is_known():
    for e in TEST_SET:
        assert e.category in (CAT_PLAIN, CAT_SYNONYM)


# ── Invariant keyword ground truth ────────────────────────────────────────

@pytest.mark.parametrize("entry", TEST_SET, ids=lambda e: e.query)
def test_keywords_contain_no_seasoning(entry):
    leaked = [k for k in entry.keywords if k in SEASONINGS]
    assert not leaked, (
        f"{leaked} adalah bumbu dasar dan harus tetap di luar `keywords`; "
        "tempatnya cuma di query yang diketik"
    )


@pytest.mark.parametrize("entry", TEST_SET, ids=lambda e: e.query)
def test_keywords_are_canonical(entry):
    """Bahan bersinonim harus muncul di ground truth dengan nama kanoniknya:
    relevansi ikut maksud, bukan ejaan."""
    bad = [k for k in entry.keywords if k in NON_CANONICAL]
    assert not bad, f"{bad} harus disimpan kanonik di `keywords`"


@pytest.mark.parametrize("entry", TEST_SET, ids=lambda e: e.query)
def test_query_has_at_least_two_core_ingredients(entry):
    """Dengan 1 bahan inti, tiap resep yang memakainya jadi relevan sehingga
    Precision@5 otomatis 1.0 dan query berhenti membedakan metode."""
    assert len(entry.keywords) >= 2


@pytest.mark.parametrize("entry", TEST_SET, ids=lambda e: e.query)
def test_no_keyword_subsumes_another(entry):
    """Mencantumkan "jeruk" dan "daun jeruk" sekaligus mubazir: regex \\bjeruk\\b
    sudah cocok di dalam frasa yang lebih panjang, jadi keyword pendeknya tidak
    menambah batasan. Sekadar berbagi kata tidak masalah ("bawang putih" vs
    "bawang merah" beda bahan, regex-nya tidak saling cocok)."""
    assert len(entry.keywords) == len(set(entry.keywords))
    for a in entry.keywords:
        for b in entry.keywords:
            if a is b:
                continue
            assert not set(a.split()) <= set(b.split()), (
                f"'{a}' is subsumed by '{b}' in {entry.query!r}; "
                "the shorter keyword adds no constraint"
            )


def test_synonym_subset_actually_uses_non_canonical_spellings():
    """Otherwise the subset would be indistinguishable from the plain one."""
    for e in TEST_SET:
        if e.category != CAT_SYNONYM:
            continue
        typed = {p.strip().lower() for p in e.query.split(",")}
        assert typed & NON_CANONICAL, f"{e.query!r} tidak memuat ejaan sinonim"


def test_plain_subset_uses_only_canonical_spellings():
    for e in TEST_SET:
        if e.category != CAT_PLAIN:
            continue
        typed = {p.strip().lower() for p in e.query.split(",")}
        assert not (typed & NON_CANONICAL), f"{e.query!r} memuat ejaan sinonim"


def test_the_paired_queries_share_a_ground_truth():
    """Query 1 dan 2 permintaan yang sama dalam dua ejaan; keyword identik
    berarti selisih Precision@5 di antara keduanya murni dari retrieval."""
    plain = next(e for e in TEST_SET if e.query == "ikan, bawang merah, cabai")
    syn   = next(e for e in TEST_SET if e.query == "seafood, bawang merah, cabe")
    assert plain.keywords == syn.keywords
    assert (plain.expected_gt_min, plain.expected_gt_max) == (
        syn.expected_gt_min, syn.expected_gt_max
    )


# ── Ekspektasi ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("entry", TEST_SET, ids=lambda e: e.query)
def test_gt_band_is_a_valid_non_empty_range(entry):
    assert 0 < entry.expected_gt_min <= entry.expected_gt_max


def test_precision_target_is_uniform_and_attainable():
    """Target per-query yang dipaskan ke skor terukur akan sirkular; ambangnya
    satu nilai tetap yang boleh saja tidak dicapai sebuah query."""
    assert 0.0 < TARGET_RATIO <= 1.0
    # Harus jatuh di langkah P@5 yang bisa dicapai (kelipatan 1/K).
    assert (TARGET_RATIO * K) == pytest.approx(round(TARGET_RATIO * K))


# ── Ekspektasi recall ─────────────────────────────────────────────────────

def test_recall_ceiling_shrinks_as_ground_truth_grows():
    """Hanya K hasil yang kembali, jadi GT besar membatasi recall secara
    aritmetika, bukan karena kelemahan sistem."""
    assert recall_ceiling(4) == pytest.approx(1.0)      # GT lebih kecil dari K
    assert recall_ceiling(5) == pytest.approx(1.0)
    assert recall_ceiling(10) == pytest.approx(0.5)
    assert recall_ceiling(1089) == pytest.approx(5 / 1089)


def test_recall_ceiling_of_empty_ground_truth_is_zero():
    assert recall_ceiling(0) == 0.0


def test_expected_recall_is_a_share_of_what_is_attainable():
    """Ambang recall tetap akan menggagalkan sebagian besar query karena
    aritmetika; ekspektasi ini diskala terhadap plafon."""
    for gt in (8, 44, 289, 1089):
        assert expected_recall(gt) == pytest.approx(TARGET_RATIO * recall_ceiling(gt))
        assert expected_recall(gt) <= recall_ceiling(gt)


def test_expected_recall_is_not_rounded_up():
    """Membulatkan ambang ke 4 desimal menaikkannya di atas nilai eksak untuk
    GT besar (GT=1089 -> 0.0036730... jadi 0.0037), yang akan menggagalkan query
    yang tepat menyentuh target precision."""
    gt = 1089
    exact = TARGET_RATIO * (K / gt)
    assert expected_recall(gt) <= exact
    assert expected_recall(gt) < round(exact, 4)


def test_recall_verdict_mirrors_precision_when_gt_is_at_least_k():
    """Bukan dua uji independen: untuk GT >= K, recall@K == precision@K * K/GT,
    jadi melewati TARGET_RATIO dari plafon recall adalah kondisi yang sama dengan
    melewati TARGET_RATIO dari precision. Didokumentasikan supaya kedua kolom tak
    pernah disajikan sebagai bukti terpisah."""
    for gt in (8, 44, 289, 1089):
        for hits in range(K + 1):
            precision = hits / K
            recall = hits / gt
            assert (precision >= TARGET_RATIO) == (recall >= expected_recall(gt) - 1e-9)


# ── Metrik ────────────────────────────────────────────────────────────────

def test_reported_k_is_five():
    assert K == 5


def test_precision_and_recall():
    retrieved = ["a", "b", "c", "d", "e"]
    relevant = {"a", "c", "x", "y"}
    assert _precision(retrieved, relevant) == pytest.approx(2 / 5)
    assert _recall(retrieved, relevant) == pytest.approx(2 / 4)


def test_precision_of_empty_retrieval_is_zero():
    # split_known_ingredients() bisa saja mengembalikan kosong (semua token
    # luar-domain); itu harus bernilai 0, bukan error.
    assert _precision([], {"a"}) == 0.0


def test_recall_with_empty_ground_truth_is_zero():
    assert _recall(["a"], set()) == 0.0


def test_f1_is_zero_when_both_inputs_are_zero():
    assert _f1(0.0, 0.0) == 0.0


def test_summarise_reports_at_k_only():
    block = _summarise([(1.0, 0.5), (0.0, 0.1)])
    assert block["n"] == 2
    assert block[f"avg_precision_at_{K}"] == pytest.approx(0.5)
    assert block[f"avg_recall_at_{K}"] == pytest.approx(0.3)
    assert not any("_at_10" in key for key in block), "metrik K=10 sudah dihapus"
