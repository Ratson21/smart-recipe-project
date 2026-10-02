"""
Query-understanding tests for RecommendationEngine.

These cover the two behaviours that let the engine honour the *intent* of the
ingredients a user types, rather than dropping anything that isn't a literal
catalog word:

  1. Per-word gate - a multi-word phrase survives if AT LEAST ONE of its words
     is a known ingredient, so semantic phrases like "daging unggas" reach the
     encoder (and can match poultry) instead of being discarded wholesale.
  2. Fuzzy typo correction - small typos ("ayma", "puith") snap to the nearest
     known ingredient before the gate, so a mistyped ingredient still searches.

Genuinely out-of-domain tokens (every word unknown, far from any ingredient)
are still dropped and reported, so the UI can explain them.

Pure unit tests: the engine's vocabulary is injected directly, so no model or
database is required.
"""

from app.services.recommendation_engine import RecommendationEngine


def _engine_with_vocab(words):
    """An engine whose known-ingredient vocabulary is exactly `words`."""
    eng = RecommendationEngine()
    eng.recipe_vocab = frozenset(words)
    return eng


# Per-word gate

def test_phrase_kept_when_one_word_known():
    # "segar" never appears as a catalog ingredient word, but "daging" does -
    # the phrase carries real intent and must survive to the semantic encoder
    # rather than being dropped wholesale.
    eng = _engine_with_vocab({"daging", "ayam", "tomat"})

    known, ignored = eng.split_known_ingredients("daging segar")

    assert "daging segar" in known
    assert ignored == []


def test_fully_unknown_token_dropped_and_reported():
    eng = _engine_with_vocab({"ayam", "tomat", "bawang"})

    known, ignored = eng.split_known_ingredients("xyzbukanbahan")

    assert known == ""
    assert ignored == ["xyzbukanbahan"]


def test_known_word_passes_through_unchanged():
    eng = _engine_with_vocab({"ayam", "tomat"})

    known, ignored = eng.split_known_ingredients("ayam")

    assert known == "ayam"
    assert ignored == []


def test_mixed_known_and_garbage():
    eng = _engine_with_vocab({"ayam", "tomat"})

    known, ignored = eng.split_known_ingredients("ayam, xyzbukanbahan")

    assert "ayam" in known
    assert "xyzbukanbahan" not in known
    assert ignored == ["xyzbukanbahan"]


# Fuzzy typo correction

def test_transposition_typo_corrected():
    # "ayma" -> "ayam" (last two letters transposed): Damerau distance 1.
    eng = _engine_with_vocab({"ayam", "tomat", "bawang", "putih"})

    known, ignored = eng.split_known_ingredients("ayma")

    assert "ayam" in known
    assert ignored == []


def test_typo_corrected_inside_phrase():
    # "puith" -> "putih" inside "bawang puith".
    eng = _engine_with_vocab({"bawang", "putih", "ayam"})

    known, ignored = eng.split_known_ingredients("bawang puith")

    assert "bawang putih" in known
    assert ignored == []


def test_garbage_is_not_force_corrected():
    # A token far from every known word must NOT be snapped onto an ingredient;
    # it stays unknown and is reported.
    eng = _engine_with_vocab({"ayam", "tomat", "bawang"})

    known, ignored = eng.split_known_ingredients("xyzbukanbahan")

    assert known == ""
    assert ignored == ["xyzbukanbahan"]


# Vocabulary construction

def test_build_vocab_collects_words_meeting_min_docs():
    eng = RecommendationEngine()
    eng.recipe_words = [
        frozenset({"ayam", "bawang", "putih"}),
        frozenset({"ayam", "tomat"}),
        frozenset({"tahu", "tempe"}),
    ]

    eng._build_vocab()

    assert "ayam" in eng.recipe_vocab
    assert "tomat" in eng.recipe_vocab
    assert "tempe" in eng.recipe_vocab
    assert "unggas" not in eng.recipe_vocab
