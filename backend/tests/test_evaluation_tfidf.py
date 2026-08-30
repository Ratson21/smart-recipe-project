"""
Unit test untuk baseline TF-IDF di evaluasi.

Dua sifat baseline dikunci di sini: (1) retrieval murni lexical overlap, dan
(2) menerima query mentah tanpa normalisasi sinonim/typo. Kalau suatu saat
baseline diam-diam dialihkan lewat split_known_ingredients(), klaim di skripsi
ikut berubah, jadi test_tfidf_does_not_normalise_synonyms akan gagal.

Murni unit test: tanpa model, tanpa database.
"""

from app.routes.evaluation import (
    K,
    LABEL_SYSTEM,
    LABEL_TFIDF,
    LABEL_TIE,
    TARGET_RATIO,
    TEST_SET,
    _build_tfidf_model,
    _query_row,
    _search_tfidf,
    _winner,
)

# Catatan: tiap term yang dipakai test harus muncul di minimal DUA dokumen,
# karena min_df=2 membuang term yang lebih langka dari vocabulary. "garam" dan
# "tempe" muncul sekali saja jadi memang tidak ada di vocabulary.
FIXTURE_IDS = ["r1", "r2", "r3", "r4"]
FIXTURE_TEXTS = [
    "ayam, bawang putih, garam",
    "ayam, bawang merah, cabai",
    "ikan, bawang putih, cabai",
    "ikan, tempe, bawang merah",
]


def _model():
    return _build_tfidf_model(FIXTURE_IDS, FIXTURE_TEXTS)


def test_build_produces_one_row_per_recipe():
    model = _model()
    assert model["matrix"].shape[0] == len(FIXTURE_IDS)
    assert model["ids"] == FIXTURE_IDS


def test_vocabulary_is_not_empty():
    assert len(_model()["vectorizer"].vocabulary_) > 0


def test_search_returns_at_most_k_ids():
    model = _model()
    assert len(_search_tfidf(model, "ayam", 2)) == 2
    assert len(_search_tfidf(model, "ayam", 99)) == len(FIXTURE_IDS)


def test_search_returns_ids_from_the_model():
    model = _model()
    assert set(_search_tfidf(model, "ayam, bawang putih", 4)) <= set(FIXTURE_IDS)


def test_search_ranks_exact_ingredient_overlap_first():
    model = _model()
    assert _search_tfidf(model, "ayam, bawang putih", 1) == ["r1"]


def test_tfidf_does_not_normalise_synonyms():
    """Baseline melihat query mentah: "seafood" bukan term korpus jadi tak cocok
    apa pun. Kamus seafood -> ikan ada di lapisan query understanding yang
    sengaja dilewati baseline. Assert pada vektor query (bukan ranking) supaya
    deterministik: untuk query di luar vocabulary semua similarity 0.0."""
    vec = _model()["vectorizer"]
    assert vec.transform(["ikan"]).nnz > 0
    assert vec.transform(["seafood"]).nnz == 0


# ── Kontrak response: sistem vs baseline ───────────────────────────────────

_VERDICT_FIELDS = ("meets_precision_target", "meets_recall_target", "gt_within_expected")


def _row():
    return _query_row(TEST_SET[0], gt_size=100, p=0.8, r=0.04, tp=0.6, tr=0.03)


def test_row_reports_both_methods():
    row = _row()
    assert row[f"precision_at_{K}"] == 0.8
    assert row[f"tfidf_precision_at_{K}"] == 0.6
    assert row[f"recall_at_{K}"] == 0.04
    assert row[f"tfidf_recall_at_{K}"] == 0.03


def test_baseline_carries_no_verdict_or_expectation_fields():
    """Target hanya untuk sistem; baseline tidak dinilai terhadapnya."""
    tfidf_keys = [k for k in _row() if k.startswith("tfidf_")]
    assert tfidf_keys, "expected tfidf_* fields on the row"
    for key in tfidf_keys:
        assert "expected" not in key
        assert "meets" not in key
        assert "target" not in key


def test_row_has_a_single_shared_ground_truth():
    """Satu ground truth per query, dipakai kedua metode. Kalau baseline diberi
    aturan relevansi sendiri, akan muncul field ground-truth khusus baseline."""
    row = _row()
    assert row["ground_truth_size"] == 100
    assert not any("ground_truth" in k for k in row if k.startswith("tfidf"))


def test_verdicts_are_computed_from_the_system_not_the_baseline():
    """Baseline yang kuat tidak boleh membalik verdict sistem."""
    weak_system = _query_row(TEST_SET[0], gt_size=100, p=0.2, r=0.01, tp=1.0, tr=0.05)
    assert weak_system["meets_precision_target"] is False


def test_row_keeps_the_existing_field_names():
    row = _row()
    for key in ("query", "keywords", "category", "expected_gt_min", "expected_gt_max",
                "ground_truth_size", f"expected_precision_at_{K}",
                f"expected_recall_at_{K}", f"recall_ceiling_at_{K}", *_VERDICT_FIELDS):
        assert key in row


def test_precision_verdict_uses_the_uniform_target():
    assert _query_row(TEST_SET[0], 100, TARGET_RATIO, 0.04, 0.0, 0.0)["meets_precision_target"] is True
    assert _query_row(TEST_SET[0], 100, TARGET_RATIO - 0.01, 0.04, 0.0, 0.0)["meets_precision_target"] is False


# ── Verdict head-to-head ──────────────────────────────────────────────────

def test_winner_is_the_higher_score():
    assert _winner(0.96, 0.31) == LABEL_SYSTEM
    assert _winner(0.31, 0.96) == LABEL_TFIDF


def test_equal_scores_are_a_tie_not_a_system_win():
    """Seri tidak boleh dihitung sebagai menang; 2 dari 20 query memang seri."""
    assert _winner(0.4, 0.4) == LABEL_TIE
    assert _winner(0.0, 0.0) == LABEL_TIE


def test_row_declares_a_winner_from_precision():
    assert _query_row(TEST_SET[0], 100, 1.0, 0.05, 0.2, 0.01)["winner"] == LABEL_SYSTEM
    assert _query_row(TEST_SET[0], 100, 0.2, 0.01, 1.0, 0.05)["winner"] == LABEL_TFIDF
    assert _query_row(TEST_SET[0], 100, 0.4, 0.02, 0.4, 0.02)["winner"] == LABEL_TIE


def test_winner_is_decided_on_rounded_scores_shown_to_the_reader():
    """Verdict harus cocok dengan angka yang ditampilkan. Membandingkan float
    mentah bisa membuat baris menampilkan 0.40 vs 0.40 tapi menyatakan pemenang
    dari selisih yang tak terlihat pembaca."""
    row = _query_row(TEST_SET[0], 100, 0.400001, 0.02, 0.4, 0.02)
    assert row["precision_at_5"] == row["tfidf_precision_at_5"] == 0.4
    assert row["winner"] == LABEL_TIE
