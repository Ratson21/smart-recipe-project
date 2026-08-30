"""
Category-synonym normalisation tests for the ingredient cleaner.

Broad culinary categories a user might type get normalised to a concrete,
catalog-present ingredient, so semantic search targets the right dishes instead
of a vague average:

  * "unggas" (poultry)       -> "ayam"
  * "seafood"                -> "ikan"
  * "sayuran hijau" (greens) -> "bayam"

Single-word categories use the word-level SYNONYMS map; the multi-word
"sayuran hijau" uses the phrase-level pass. Existing single-word synonyms must
keep working.
"""

from app.services.weighted_encoder import _clean_ingredient


def test_unggas_maps_to_ayam():
    assert _clean_ingredient("unggas") == "ayam"


def test_daging_unggas_normalises_poultry_word():
    # The "unggas" word is normalised in place, so the phrase targets chicken
    # instead of being pulled toward red meat by "daging".
    assert _clean_ingredient("daging unggas") == "daging ayam"


def test_seafood_maps_to_ikan():
    assert _clean_ingredient("seafood") == "ikan"


def test_sayuran_hijau_maps_to_bayam():
    assert _clean_ingredient("sayuran hijau") == "bayam"


def test_existing_single_word_synonym_still_applies():
    assert _clean_ingredient("telor") == "telur"
