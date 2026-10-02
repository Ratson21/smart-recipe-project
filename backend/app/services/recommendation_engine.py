"""
Singleton RecommendationEngine.

Lifecycle
---------
1. Called once from FastAPI lifespan via  await engine.initialize(db).
2. Loads SentenceTransformer model (blocking -> thread executor).
3. Loads pre-computed vectors from disk, or encodes all recipes and saves them.
   Re-encodes only when:
   • data/recipe_vectors.npy does not exist, OR
   • vector count ≠ number of documents in MongoDB.
4. Exposes `engine.search(...)` for the recommendations route (added later).

Vector notes
------------
Embeddings are L2-normalised at encode time so cosine similarity reduces to
a dot product: scores = query_vec @ recipe_vectors.T  (fast numpy matmul).
"""

import asyncio
import json
import logging
import re
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from rapidfuzz import process
from rapidfuzz.distance import DamerauLevenshtein
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.services.weighted_encoder import (
    _clean_ingredient,
    _get_weight,
    encode_query,
    is_seasoning,
)

logger = logging.getLogger(__name__)

# query_score = _W_SEMANTIC·semantic + _W_LEXICAL·lexical  (must sum to 1.0).
#   semantic = meaning similarity
#   lexical  = weighted fraction of the query the recipe covers (importance-aware)
# Reverted to the semantic+lexical baseline while the ingredient-matching
# pipeline is being reconsidered. The unweighted `coverage` component (and any
# `simplicity`/buyability experiments) are intentionally left out of the score
# for now; _coverage() is kept below for when matching work resumes.
_W_SEMANTIC = 0.65
_W_LEXICAL  = 0.35

# Final-ranking tiebreaker: among recipes whose relevance scores fall in the
# same bucket of this width, prefer the one with FEWER ingredients (simpler /
# less to shop for). Wider bucket -> simplicity matters more relative to score.
_SIMPLICITY_BUCKET = 0.01

# A query ingredient is "known" if it appears in at least this many recipes
# (after spelling normalisation). Below it (e.g. "babi", absent from this halal
# Indonesian dataset), the ingredient is treated as out-of-domain: dropped from
# the search and reported back so the UI can tell the user, instead of silently
# returning unrelated dishes that look like a bug.
_MIN_INGREDIENT_DOCS = 1

# Fuzzy spelling correction. An unknown query word is snapped to the nearest
# known ingredient word when it is within this Damerau-Levenshtein distance - a
# metric that counts a single adjacent-letter transposition ("ayma"->"ayam",
# "puith"->"putih") as distance 1, which is the most common kind of typo. Very
# short words are left untouched: a 1-edit budget on a 3-letter token would snap
# half the vocabulary onto it.
_FUZZY_MIN_LEN        = 4   # don't attempt to correct words shorter than this
_FUZZY_LONG_LEN       = 8   # words at least this long may use the larger budget
_FUZZY_MAX_DIST_SHORT = 1   # edit budget for short/medium words
_FUZZY_MAX_DIST_LONG  = 2   # edit budget for long words

_DATA_DIR    = Path(__file__).resolve().parents[2] / "data"
_VECTORS_NPY = _DATA_DIR / "recipe_vectors.npy"
_IDS_JSON    = _DATA_DIR / "recipe_ids.json"

_ENCODE_BATCH = 128   # sentences per batch during bulk encode




class RecommendationEngine:
    def __init__(self) -> None:
        self.model:      Optional[SentenceTransformer] = None
        self.vectors:    Optional[np.ndarray] = None   # shape (N, 384), float32, normalised
        self.recipe_ids: list[str] = []
        # Per-recipe set of cleaned ingredient *words* - used for the lexical
        # bonus that surfaces recipes literally containing the query tokens.
        self.recipe_words: list[frozenset[str]] = []
        # Known-ingredient vocabulary (words appearing in ≥ _MIN_INGREDIENT_DOCS
        # recipes). Drives the per-word gate and fuzzy typo correction.
        self.recipe_vocab: frozenset[str] = frozenset()
        # Per-recipe ingredient count - used as the final-ranking tiebreaker so
        # simpler recipes (fewer ingredients) surface first among equals.
        self.recipe_ingredient_counts: np.ndarray = np.zeros(0, dtype=np.int32)
        self._ready:     bool = False

    # Public API

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def initialize(self, db: AsyncIOMotorDatabase) -> None:
        """Load model + vectors.  Called once from FastAPI lifespan."""
        wall = time.perf_counter()
        logger.info("RecommendationEngine - starting initialisation")

        await self._load_model()

        db_count = await db["recipes"].count_documents({})
        logger.info("MongoDB recipes count: %d", db_count)

        if self._vectors_on_disk_valid(db_count):
            await self._load_from_disk(db)
        else:
            await self._encode_and_save(db, db_count)

        self._ready = True
        logger.info(
            "RecommendationEngine ready - %d vectors, total init %.1fs",
            len(self.recipe_ids),
            time.perf_counter() - wall,
        )

    def cosine_scores(self, query_vec: np.ndarray) -> np.ndarray:
        """Return cosine similarity (dot product) of query_vec vs all recipe vectors."""
        return self.vectors @ query_vec

    async def search(
        self,
        db: AsyncIOMotorDatabase,
        query_text: str,
        user_id: Optional[str] = None,
        filters: Optional[dict] = None,
        top_n: int = 20,
    ) -> list[dict]:
        """
        Core recommendation pipeline.

        Returns list of dicts: {recipe_id, match_score, match_percentage}
        sorted descending by hybrid_score.
        """
        if filters is None:
            filters = {}

        # 1. Preprocess + encode query
        processed = self._preprocess(query_text)
        query_vec = await asyncio.to_thread(encode_query, processed, self.model)

        # 2a. Semantic cosine similarity against all recipe vectors
        semantic_scores: np.ndarray = self.cosine_scores(query_vec)

        # 2b. Lexical coverage bonus.
        # Without this, semantic-only scoring lets recipes that are mono-
        # ingredient (e.g. "Telur Dadar") beat multi-ingredient dishes
        # ("Nasi Goreng Telur") for queries like "nasi, kecap, telur":
        # the mono recipe's vector is concentrated on telur, while the
        # multi recipe's vector is diluted across nasi/telur/kecap/etc.
        # Lexical bonus rewards recipes that literally contain the query
        # tokens, weighted by INGREDIENT_WEIGHTS importance.
        lexical_scores = self._lexical_coverage(processed)

        query_scores = (
            _W_SEMANTIC * semantic_scores
            + _W_LEXICAL * lexical_scores
        )

        # 3. Optional personalisation (hybrid scoring)
        if user_id:
            taste_vec = await self._build_taste_profile(db, user_id)
            if taste_vec is not None:
                taste_scores: np.ndarray = self.cosine_scores(taste_vec)
                hybrid = 0.7 * query_scores + 0.3 * taste_scores
            else:
                hybrid = query_scores
        else:
            hybrid = query_scores

        # 4. Apply MongoDB-side filters (fetch matching ids first, then mask)
        allowed_ids: Optional[set[str]] = await self._filter_ids(db, filters) if filters else None

        # 5. Build ranked results.
        # Primary key: relevance, bucketed to _SIMPLICITY_BUCKET so near-equal
        # scores tie. Secondary key: fewer ingredients first. np.lexsort takes
        # the LAST key as primary, ascending - so negate the bucketed score
        # (best relevance first) and keep ingredient count ascending.
        bucketed = np.round(hybrid / _SIMPLICITY_BUCKET)
        ranked_idx = np.lexsort((self.recipe_ingredient_counts, -bucketed))
        results = []
        for idx in ranked_idx:
            rid = self.recipe_ids[idx]
            if allowed_ids is not None and rid not in allowed_ids:
                continue
            score = float(hybrid[idx])
            results.append({
                "recipe_id": rid,
                "match_score": round(score, 4),
                "match_percentage": max(0, round(score * 100)),
            })
            if len(results) >= top_n:
                break

        return results

    def _build_vocab(self) -> None:
        """Build the known-ingredient vocabulary from the per-recipe word sets.

        A word is "known" if it appears (as a cleaned token) in at least
        _MIN_INGREDIENT_DOCS recipes. This vocabulary drives both the per-word
        gate and fuzzy typo correction in split_known_ingredients().
        """
        df: Counter[str] = Counter()
        for rw in self.recipe_words:
            df.update(rw)
        self.recipe_vocab = frozenset(
            w for w, c in df.items() if c >= _MIN_INGREDIENT_DOCS
        )

    def _correct_word(self, word: str) -> str:
        """Snap a single word to the nearest known ingredient word when it is a
        small typo away; otherwise return it unchanged.

        Known words and very short tokens are returned as-is. Words with no
        match inside the edit-distance budget (genuine non-ingredients) are
        left untouched so the gate can drop them.
        """
        if not word or word in self.recipe_vocab or len(word) < _FUZZY_MIN_LEN:
            return word
        if not self.recipe_vocab:
            return word
        max_dist = (
            _FUZZY_MAX_DIST_LONG if len(word) >= _FUZZY_LONG_LEN else _FUZZY_MAX_DIST_SHORT
        )
        match = process.extractOne(
            word,
            self.recipe_vocab,
            scorer=DamerauLevenshtein.distance,
            score_cutoff=max_dist,
        )
        return match[0] if match else word

    def _correct_phrase(self, cleaned_phrase: str) -> str:
        """Apply _correct_word to every word in an already-cleaned phrase."""
        return " ".join(self._correct_word(w) for w in cleaned_phrase.split())

    def split_known_ingredients(self, query_text: str) -> tuple[str, list[str]]:
        """
        Partition the comma-separated query into in-domain ingredients vs
        out-of-domain tokens, fixing small typos along the way.

        Returns (corrected_query_of_known_ingredients, [unknown_token_texts]).

        Each comma-part is cleaned, then each word is fuzzy-corrected to the
        nearest known ingredient (so "ayma"->"ayam", "bawang puith"->"bawang
        putih"). A part is "known" if AT LEAST ONE of its words is in the
        vocabulary - so a semantic phrase like "daging unggas" survives via its
        known word ("daging") and reaches the encoder, where it can match
        poultry, instead of being discarded just because "unggas" never appears
        literally in any recipe. Only parts whose every word is out-of-domain
        (e.g. "xyzbukanbahan") are dropped, and reported with the user's
        ORIGINAL spelling so the UI can echo what they typed.
        """
        known_parts: list[str] = []
        unknown_parts: list[str] = []
        for raw in query_text.split(","):
            original = raw.strip()
            if not original:
                continue
            corrected = self._correct_phrase(_clean_ingredient(original))
            words = frozenset(corrected.split())
            if not words:
                continue
            if any(w in self.recipe_vocab for w in words):
                known_parts.append(corrected)
            else:
                unknown_parts.append(original)
        return ", ".join(known_parts), unknown_parts

    async def similar(self, recipe_id: str, top_n: int = 6) -> list[dict]:
        """Return top_n most-similar recipe ids (excluding the query recipe itself)."""
        try:
            idx = self.recipe_ids.index(recipe_id)
        except ValueError:
            return []
        query_vec = self.vectors[idx]
        scores: np.ndarray = self.cosine_scores(query_vec)
        ranked = np.argsort(scores)[::-1]
        results = []
        for i in ranked:
            if self.recipe_ids[i] == recipe_id:
                continue
            results.append({
                "recipe_id": self.recipe_ids[i],
                "match_score": round(float(scores[i]), 4),
                "match_percentage": max(0, round(float(scores[i]) * 100)),
            })
            if len(results) >= top_n:
                break
        return results

    # Private search helpers

    def _lexical_coverage(self, query_text: str) -> np.ndarray:
        """
        Per-recipe lexical coverage of query ingredients, weighted by
        INGREDIENT_WEIGHTS. Result is in [0, 1] - 1.0 means every query
        ingredient appears as a word in the recipe's ingredient list.

        Multi-word query tokens (e.g. "bawang putih") require ALL their
        words to be present in the recipe.
        """
        if not self.recipe_words:
            return np.zeros(len(self.recipe_ids), dtype=np.float32)

        parts = [_clean_ingredient(p) for p in query_text.split(",") if p.strip()]
        if not parts:
            return np.zeros(len(self.recipe_ids), dtype=np.float32)

        token_word_sets = [frozenset(t.split()) for t in parts]
        token_weights   = [_get_weight(t)      for t in parts]
        total_w = float(sum(token_weights)) or 1.0

        scores = np.zeros(len(self.recipe_words), dtype=np.float32)
        for i, recipe_set in enumerate(self.recipe_words):
            matched = 0.0
            for words, w in zip(token_word_sets, token_weights):
                if words and words.issubset(recipe_set):
                    matched += w
            scores[i] = matched / total_w
        return scores

    def _coverage(self, query_text: str) -> np.ndarray:
        """
        Unweighted fraction of DISTINCT query ingredients a recipe contains:
        (# query ingredients present) / (total query ingredients).

        Unlike _lexical_coverage, every query ingredient counts equally - so a
        recipe matching only the single heaviest ingredient scores low, and a
        recipe using several of the user's ingredients scores high. This is what
        pulls multi-ingredient dishes above mono-ingredient ones.
        """
        n_recipes = len(self.recipe_ids)
        if not self.recipe_words:
            return np.zeros(n_recipes, dtype=np.float32)

        parts = [_clean_ingredient(p) for p in query_text.split(",") if p.strip()]
        token_word_sets = [frozenset(t.split()) for t in parts if t.split()]
        n = len(token_word_sets)
        if n == 0:
            return np.zeros(n_recipes, dtype=np.float32)

        scores = np.zeros(len(self.recipe_words), dtype=np.float32)
        for i, recipe_set in enumerate(self.recipe_words):
            matched = sum(1 for words in token_word_sets if words.issubset(recipe_set))
            scores[i] = matched / n
        return scores

    @staticmethod
    def _preprocess(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[0-9]+[.,]?[0-9]*\s*\w{0,5}\b", " ", text)
        text = re.sub(r"[^\w\s,]", " ", text)
        return " ".join(text.split())

    async def _build_taste_profile(
        self, db: AsyncIOMotorDatabase, user_id: str
    ) -> Optional[np.ndarray]:
        """Average vector of recipes rated ≥4 or bookmarked by the user."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None

        # Collect recipe ids from ratings + bookmarks in parallel
        rated_cursor = db["ratings"].find(
            {"user_id": oid, "rating_score": {"$gte": 4}}, {"recipe_id": 1}
        )
        bookmark_cursor = db["bookmarks"].find({"user_id": oid}, {"recipe_id": 1})
        rated_docs, bm_docs = await asyncio.gather(
            rated_cursor.to_list(length=None),
            bookmark_cursor.to_list(length=None),
        )
        ids = {str(d["recipe_id"]) for d in rated_docs + bm_docs}
        if not ids:
            return None

        indices = [i for i, rid in enumerate(self.recipe_ids) if rid in ids]
        if not indices:
            return None

        avg = self.vectors[indices].mean(axis=0).astype(np.float32)
        norm = np.linalg.norm(avg)
        if norm > 1e-9:
            avg /= norm
        return avg

    async def _filter_ids(self, db: AsyncIOMotorDatabase, filters: dict) -> Optional[set[str]]:
        """Return set of recipe_id strings that pass all filters, or None if no filters."""
        query: dict = {}
        if filters.get("difficulty"):
            query["difficulty_level"] = filters["difficulty"]
        if filters.get("max_time"):
            query["estimated_time_minutes"] = {"$lte": int(filters["max_time"])}
        if not query:
            return None
        docs = await db["recipes"].find(query, {"_id": 1}).to_list(length=None)
        return {str(d["_id"]) for d in docs}

    # Private load helpers

    async def _load_model(self) -> None:
        t = time.perf_counter()
        logger.info("Loading SentenceTransformer '%s' ...", settings.model_name)
        self.model = await asyncio.to_thread(
            SentenceTransformer, settings.model_name
        )
        logger.info("Model loaded in %.1fs", time.perf_counter() - t)

    def _vectors_on_disk_valid(self, db_count: int) -> bool:
        if not _VECTORS_NPY.exists() or not _IDS_JSON.exists():
            logger.info("No cached vectors found on disk")
            return False
        vec = np.load(str(_VECTORS_NPY), mmap_mode="r")
        if vec.shape[0] != db_count:
            logger.info(
                "Vector count mismatch: disk=%d  db=%d - will re-encode",
                vec.shape[0], db_count,
            )
            return False
        return True

    async def _load_from_disk(self, db: AsyncIOMotorDatabase) -> None:
        t = time.perf_counter()
        logger.info("Loading vectors from disk ...")
        self.vectors = await asyncio.to_thread(
            np.load, str(_VECTORS_NPY)
        )
        with open(_IDS_JSON, encoding="utf-8") as fh:
            self.recipe_ids = json.load(fh)

        # Word sets for the lexical bonus aren't cached - they're cheap to
        # rebuild and stay in lock-step with the live MongoDB content.
        docs = await db["recipes"].find(
            {"_id": {"$in": [ObjectId(rid) for rid in self.recipe_ids]}},
            {"_id": 1, "ingredients_cleaned": 1},
        ).to_list(length=None)
        by_id = {str(d["_id"]): d.get("ingredients_cleaned", "") for d in docs}
        texts = [by_id.get(rid, "") for rid in self.recipe_ids]
        self.recipe_words = self._build_word_sets(texts)
        self._build_vocab()
        self.recipe_ingredient_counts = self._build_counts(texts)

        logger.info(
            "Loaded %d × %d vectors from disk in %.2fs",
            *self.vectors.shape,
            time.perf_counter() - t,
        )

    async def _encode_and_save(self, db: AsyncIOMotorDatabase, db_count: int) -> None:
        t = time.perf_counter()
        logger.info("Fetching ingredients from MongoDB ...")
        docs = await db["recipes"].find(
            {}, {"_id": 1, "ingredients_cleaned": 1}
        ).to_list(length=None)

        recipe_ids  = [str(doc["_id"]) for doc in docs]
        texts       = [doc.get("ingredients_cleaned", "") for doc in docs]

        logger.info(
            "Encoding %d texts with batch_size=%d (this may take several minutes on first run) ...",
            db_count, _ENCODE_BATCH,
        )
        vectors: np.ndarray = await asyncio.to_thread(
            self._encode_texts, texts
        )

        logger.info("Encoding done in %.1fs - saving to disk ...", time.perf_counter() - t)
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(np.save, str(_VECTORS_NPY), vectors)
        with open(_IDS_JSON, "w", encoding="utf-8") as fh:
            json.dump(recipe_ids, fh)

        self.vectors      = vectors
        self.recipe_ids   = recipe_ids
        self.recipe_words = self._build_word_sets(texts)
        self._build_vocab()
        self.recipe_ingredient_counts = self._build_counts(texts)
        logger.info("Vectors saved: %s (%.1f MB)", _VECTORS_NPY, _VECTORS_NPY.stat().st_size / 1e6)

    @staticmethod
    def _build_word_sets(texts: list[str]) -> list[frozenset[str]]:
        """Per-recipe lowercase word set across cleaned ingredient tokens."""
        out: list[frozenset[str]] = []
        for raw in texts:
            words: set[str] = set()
            for part in (raw or "").split(","):
                part = part.strip()
                if not part:
                    continue
                cleaned = _clean_ingredient(part)
                if is_seasoning(cleaned):
                    continue  # don't let "kaldu sapi" leak "sapi" into matching
                for w in cleaned.split():
                    if w:
                        words.add(w)
            out.append(frozenset(words))
        return out

    @staticmethod
    def _build_counts(texts: list[str]) -> np.ndarray:
        """Per-recipe ingredient count (non-empty comma tokens of ingredients_cleaned)."""
        counts = [
            sum(1 for part in (raw or "").split(",") if part.strip())
            for raw in texts
        ]
        return np.array(counts, dtype=np.int32)

    def _encode_texts(self, texts: list[str]) -> np.ndarray:
        """
        Weighted per-ingredient encoding for the catalog.

        Mirrors the query-side `encode_query` pipeline so query and catalog
        live in the same vector geometry - without this symmetry, a query
        like "nasi, kecap, telur" never lands near a "nasi goreng" recipe
        because the recipe was encoded as one averaged blob while the query
        is a weighted average of single-ingredient vectors.

        Optimisation: ingredients repeat heavily across 14 945 recipes
        (garam, bawang putih, gula, ...), so we de-duplicate and encode each
        unique token only once.
        """
        # Pass 1 - tokenise every recipe.
        per_recipe: list[tuple[list[int], np.ndarray]] = []
        unique: dict[str, int] = {}  # token -> index in `unique_tokens`
        unique_tokens: list[str] = []

        for raw in texts:
            parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
            if not parts:
                parts = ["bahan"]
            cleaned = [_clean_ingredient(p) for p in parts]
            indices: list[int] = []
            for tok in cleaned:
                idx = unique.get(tok)
                if idx is None:
                    idx = len(unique_tokens)
                    unique[tok] = idx
                    unique_tokens.append(tok)
                indices.append(idx)
            weights = np.array([_get_weight(c) for c in cleaned], dtype=np.float32)
            per_recipe.append((indices, weights))

        logger.info(
            "Weighted encoding: %d recipes, %d unique ingredient tokens",
            len(texts), len(unique_tokens),
        )

        # Pass 2 - encode every unique token once (unnormalised - we average
        # then normalise at the end, matching encode_query).
        unique_vecs: np.ndarray = self.model.encode(
            unique_tokens,
            batch_size=_ENCODE_BATCH,
            show_progress_bar=True,
            normalize_embeddings=False,
            convert_to_numpy=True,
        ).astype(np.float32)

        # Pass 3 - per-recipe weighted average + L2 normalise.
        out = np.empty((len(texts), unique_vecs.shape[1]), dtype=np.float32)
        for i, (indices, w) in enumerate(per_recipe):
            v = np.average(unique_vecs[indices], axis=0, weights=w).astype(np.float32)
            n = float(np.linalg.norm(v))
            if n > 1e-9:
                v /= n
            out[i] = v
        return out


# Module-level singleton - import this everywhere
engine = RecommendationEngine()
