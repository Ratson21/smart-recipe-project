from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models.recipe import RecipeCard
from app.services.recommendation_engine import engine

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


# ── Request / Response schemas ────────────────────────────────────────────

class SearchFilters(BaseModel):
    max_time: Optional[int] = Field(None, ge=1, description="Maks waktu masak (menit)")
    difficulty: Optional[str] = Field(None, description="Mudah | Sedang | Sulit")


class SmartSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Bahan-bahan yang dimiliki, pisahkan koma")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    top_n: int = Field(20, ge=1, le=100)


class RecipeMatch(BaseModel):
    recipe: RecipeCard
    match_score: float
    match_percentage: int


class SmartSearchResponse(BaseModel):
    results: list[RecipeMatch]
    total: int
    query_processed: str
    is_personalized: bool
    ignored_ingredients: list[str] = []  # query ingredients not found in the dataset


# ── Serializer ────────────────────────────────────────────────────────────

def _to_card(doc: dict) -> RecipeCard:
    return RecipeCard(
        id=str(doc["_id"]),
        title=doc["title"],
        category=doc.get("category", ""),
        total_ingredients=doc.get("total_ingredients", 0),
        total_steps=doc.get("total_steps", 0),
        estimated_time_minutes=doc.get("estimated_time_minutes", 0),
        difficulty_level=doc.get("difficulty_level", ""),
        average_rating=doc.get("average_rating", 0.0),
        total_reviews=doc.get("total_reviews", 0),
        ingredients_cleaned=doc.get("ingredients_cleaned", ""),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/smart-search",
    response_model=SmartSearchResponse,
    summary="Core AI: cari resep berdasarkan bahan yang dimiliki",
)
async def smart_search(
    body: SmartSearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    if not engine.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation engine belum siap",
        )

    user_id = str(current_user["_id"]) if current_user else None
    filters = body.filters.model_dump(exclude_none=True)

    # Drop ingredients absent from the dataset (e.g. "babi") so they don't pull
    # in unrelated dishes; report them so the UI can tell the user.
    known_query, ignored = engine.split_known_ingredients(body.query)

    if not known_query:
        # Every ingredient is out-of-domain - nothing meaningful to search.
        return SmartSearchResponse(
            results=[],
            total=0,
            query_processed=body.query,
            is_personalized=bool(user_id),
            ignored_ingredients=ignored,
        )

    ranked = await engine.search(
        db=db,
        query_text=known_query,
        user_id=user_id,
        filters=filters,
        top_n=body.top_n,
    )

    if not ranked:
        return SmartSearchResponse(
            results=[],
            total=0,
            query_processed=body.query,
            is_personalized=bool(user_id),
            ignored_ingredients=ignored,
        )

    # Fetch recipe docs in one query (preserve rank order)
    recipe_ids_ordered = [r["recipe_id"] for r in ranked]
    oids = [ObjectId(rid) for rid in recipe_ids_ordered]
    docs = await db["recipes"].find({"_id": {"$in": oids}}).to_list(length=None)
    doc_map = {str(d["_id"]): d for d in docs}

    results: list[RecipeMatch] = []
    for r in ranked:
        doc = doc_map.get(r["recipe_id"])
        if doc:
            results.append(RecipeMatch(
                recipe=_to_card(doc),
                match_score=r["match_score"],
                match_percentage=r["match_percentage"],
            ))

    return SmartSearchResponse(
        results=results,
        total=len(results),
        query_processed=body.query,
        is_personalized=bool(user_id),
        ignored_ingredients=ignored,
    )


@router.get(
    "/similar/{recipe_id}",
    response_model=list[RecipeMatch],
    summary="6 resep paling mirip berdasarkan vektor semantik",
)
async def similar_recipes(
    recipe_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not engine.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation engine belum siap",
        )

    try:
        ObjectId(recipe_id)  # validate format
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    ranked = await engine.similar(recipe_id, top_n=6)
    if not ranked:
        return []

    oids = [ObjectId(r["recipe_id"]) for r in ranked]
    docs = await db["recipes"].find({"_id": {"$in": oids}}).to_list(length=None)
    doc_map = {str(d["_id"]): d for d in docs}

    results: list[RecipeMatch] = []
    for r in ranked:
        doc = doc_map.get(r["recipe_id"])
        if doc:
            results.append(RecipeMatch(
                recipe=_to_card(doc),
                match_score=r["match_score"],
                match_percentage=r["match_percentage"],
            ))

    return results
