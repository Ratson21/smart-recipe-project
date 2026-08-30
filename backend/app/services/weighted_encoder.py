"""
WeightedIngredientEncoder

Encodes a comma-separated ingredient string into a single 384-dim vector
by averaging per-ingredient embeddings with category-based weights.
Normalised at the end so the result is unit-length (cosine = dot product).
"""

import re

import numpy as np
from sentence_transformers import SentenceTransformer

INGREDIENT_WEIGHTS: dict[str, float] = {
    # Karbohidrat utama / staples - 3.0
    # Defines the dish identity (nasi goreng, mie ayam, dll). Tanpa ini,
    # query seperti "nasi, kecap, telur" akan didominasi `telur` (2.5)
    # dan tidak pernah memunculkan resep nasi/mie sebagai hasil utama.
    "nasi": 3.0, "mie": 3.0, "mi ": 3.0, "bihun": 3.0, "kwetiau": 3.0,
    "kwetiaw": 3.0, "spaghetti": 3.0, "spageti": 3.0, "pasta": 3.0,
    "makaroni": 3.0, "ubi": 3.0,
    # Roti / olahan tepung - 2.5 (biasanya lauk pendamping, bukan staple utama)
    "roti": 2.5,
    # Protein utama - 3.0
    "ayam": 3.0, "daging": 3.0, "ikan": 3.0, "udang": 3.0,
    "cumi": 3.0, "kepiting": 3.0, "bebek": 3.0, "kambing": 3.0,
    "sapi": 3.0, "babi": 3.0, "lele": 3.0, "gurame": 3.0,
    "nila": 3.0, "tongkol": 3.0, "cakalang": 3.0, "bandeng": 3.0,
    # Protein nabati - 2.5
    "tahu": 2.5, "tempe": 2.5, "kacang": 2.5, "telur": 2.5,
    "edamame": 2.5, "kedelai": 2.5,
    # Sayuran utama - 2.0
    "wortel": 2.0, "kentang": 2.0, "bayam": 2.0, "kangkung": 2.0,
    "terong": 2.0, "labu": 2.0, "jagung": 2.0, "buncis": 2.0,
    "kol": 2.0, "kubis": 2.0, "brokoli": 2.0, "sawi": 2.0,
    "pare": 2.0, "nangka": 2.0, "pepaya": 2.0, "singkong": 2.0,
    "tauge": 2.0, "rebung": 2.0,
    # Bumbu aromatik - 1.5
    "bawang merah": 1.5, "bawang putih": 1.5, "jahe": 1.5,
    "kunyit": 1.5, "kemiri": 1.5, "lengkuas": 1.5, "serai": 1.5,
    "kencur": 1.5, "ketumbar": 1.5, "jintan": 1.5, "kayu manis": 1.5,
    "cengkeh": 1.5, "kapulaga": 1.5, "pala": 1.5, "laos": 1.5,
    # Pelengkap - 1.0 (default)
    "tomat": 1.0, "cabai": 1.0, "cabe": 1.0, "daun salam": 1.0,
    "daun jeruk": 1.0, "peterseli": 1.0, "kemangi": 1.0,
    "daun bawang": 1.0, "seledri": 1.0, "jeruk": 1.0,
    # Santan - 1.5, sejajar bumbu aromatik, BUKAN bumbu dasar.
    # Santan menentukan identitas hidangan: "daging + santan" itu rendang/gulai,
    # sedangkan "daging + kecap + saos" itu teriyaki. Pada bobot 0.5 santan
    # tenggelam oleh protein dan query bersantan mengembalikan hidangan yang
    # sama sekali lain. Evaluasi 20-query: menaikkan 0.5 -> 1.5 memperbaiki 4
    # query (P@5 rata-rata 0.87 -> 0.96) tanpa menurunkan satu pun; di atas 1.5
    # hasilnya mendatar, jadi 1.5 adalah nilai efektif terkecil.
    "santan": 1.5,
    # Bumbu dasar - 0.5
    "garam": 0.5, "gula": 0.5, "merica": 0.5, "lada": 0.5,
    "minyak": 0.5, "kecap": 0.5, "penyedap": 0.3, "kaldu": 0.5,
    "cuka": 0.5, "tepung": 0.5, "maizena": 0.5,
}

_CLEAN_RE = re.compile(r"[0-9]+[.,]?[0-9]*\s*(gram|gr|g|kg|ml|l|liter|sdm|sdt|butir|buah|siung|lembar|batang|ruas|cm|cc|pcs|potong|iris|helai|genggam)?\s*", re.I)
_PUNCT_RE = re.compile(r"[^\w\s]")

# Spelling / synonym normalisation applied word-by-word during cleaning, so
# query and recipe ingredients land on the same canonical token. Extend freely.
SYNONYMS: dict[str, str] = {
    "toge": "tauge", "taoge": "tauge", "tauge": "tauge", "tage": "tauge", "kecambah": "tauge",
    "telor": "telur",
    "cabe": "cabai", "cabai": "cabai", "lombok": "cabai",
    "terung": "terong",
    "trasi": "terasi",
    "santen": "santan",
    "bombay": "bombai",
    "wartel": "wortel",
    "kentangnya": "kentang",
    "bdng": "bawang",  # common shorthand noise
    # Broad single-word categories -> the dominant concrete ingredient in the
    # catalog, so semantic search targets real dishes instead of a vague
    # category average (e.g. "unggas"/"daging unggas" would otherwise drift
    # toward red meat via the weight on "daging").
    "unggas": "ayam",
    "seafood": "ikan",
}

# Multi-word category phrases, normalised before the word-level SYNONYMS pass.
# A phrase can't live in SYNONYMS (matched per word), so it gets its own map.
PHRASE_SYNONYMS: dict[str, str] = {
    "sayuran hijau": "bayam",
    "sayur hijau": "bayam",
}
_PHRASE_SYNONYM_RE = {
    re.compile(rf"\b{re.escape(phrase)}\b"): canon
    for phrase, canon in PHRASE_SYNONYMS.items()
}

# Words that mark a token as a flavouring/stock product (e.g. "kaldu sapi
# bubuk", "masako sapi", "royco ayam"). Such tokens must NOT contribute their
# embedded protein word to ingredient matching - they are seasonings, not the
# meat itself. Detected via is_seasoning().
SEASONING_MARKERS: frozenset[str] = frozenset({
    "kaldu", "masako", "royco", "penyedap", "sasa", "ajinomoto",
    "totole", "knorr", "maggi", "vetsin", "micin", "msg",
})


def _clean_ingredient(text: str) -> str:
    text = _CLEAN_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    text = " ".join(text.lower().split())
    # Multi-word category phrases first (e.g. "sayuran hijau" -> "bayam") ...
    for pattern, canon in _PHRASE_SYNONYM_RE.items():
        text = pattern.sub(canon, text)
    # ... then word-level synonym normalisation.
    words = [SYNONYMS.get(w, w) for w in text.split()]
    return " ".join(words)


def is_seasoning(cleaned_token: str) -> bool:
    """True if a cleaned ingredient token is a flavouring/stock product.

    Used to keep tokens like "kaldu sapi bubuk" from satisfying a "sapi"
    query - the word "sapi" there is bouillon flavour, not actual beef.
    """
    return any(w in SEASONING_MARKERS for w in cleaned_token.split())


def _get_weight(ingredient: str) -> float:
    """Longest-match lookup in INGREDIENT_WEIGHTS (default 1.0).

    Uses the longest matching key so a specific phrase (e.g. "bawang putih")
    wins over a substring (e.g. "bawang"), and so low-weight base seasonings
    (garam, gula, minyak, penyedap) actually get their <1.0 weight applied
    instead of being clobbered by the default.
    """
    best_w = 1.0
    best_len = 0
    for key, w in INGREDIENT_WEIGHTS.items():
        if key in ingredient and len(key) > best_len:
            best_w = w
            best_len = len(key)
    return best_w


def encode_query(
    query_text: str,
    model: SentenceTransformer,
) -> np.ndarray:
    """
    Split query_text on commas, encode each ingredient, weighted-average,
    then L2-normalise -> shape (384,) float32.

    Falls back to encoding the whole string if it contains no commas.
    """
    parts = [p.strip() for p in query_text.split(",") if p.strip()]
    if not parts:
        parts = [query_text.strip()]

    cleaned = [_clean_ingredient(p) for p in parts]
    weights = np.array([_get_weight(c) for c in cleaned], dtype=np.float32)

    # encode() returns shape (len, 384)
    vecs: np.ndarray = model.encode(
        cleaned,
        batch_size=len(cleaned),
        show_progress_bar=False,
        normalize_embeddings=False,
        convert_to_numpy=True,
    )

    # weighted average
    avg = np.average(vecs, axis=0, weights=weights).astype(np.float32)

    # L2 normalise
    norm = np.linalg.norm(avg)
    if norm > 1e-9:
        avg /= norm
    return avg
