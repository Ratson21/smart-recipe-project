import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models.recipe import RecipeCard, RecipeDetail, RecipeListResponse

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])

# Projection for list endpoint - omit heavy text blobs
_LIST_PROJ = {"ingredients_raw": 0, "steps": 0}


# Serializers

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


def _to_detail(doc: dict) -> RecipeDetail:
    return RecipeDetail(
        id=str(doc["_id"]),
        title=doc["title"],
        category=doc.get("category", ""),
        total_ingredients=doc.get("total_ingredients", 0),
        total_steps=doc.get("total_steps", 0),
        estimated_time_minutes=doc.get("estimated_time_minutes", 0),
        difficulty_level=doc.get("difficulty_level", ""),
        average_rating=doc.get("average_rating", 0.0),
        total_reviews=doc.get("total_reviews", 0),
        ingredients_raw=doc.get("ingredients_raw", ""),
        ingredients_cleaned=doc.get("ingredients_cleaned", ""),
        steps=doc.get("steps", ""),
    )


def _build_query(difficulty: Optional[str], max_time: Optional[int]) -> dict:
    q: dict = {}
    if difficulty:
        q["difficulty_level"] = difficulty
    if max_time:
        q["estimated_time_minutes"] = {"$lte": max_time}
    return q


# Endpoints

@router.get(
    "",
    response_model=RecipeListResponse,
    summary="List resep dengan pagination dan filter opsional",
)
async def list_recipes(
    skip: int = Query(0, ge=0, description="Jumlah dokumen yang dilewati"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah dokumen per halaman"),
    difficulty: Optional[str] = Query(None, description="Filter: Mudah | Sedang | Sulit"),
    max_time: Optional[int] = Query(None, ge=1, description="Filter: maks waktu masak (menit)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = _build_query(difficulty, max_time)

    total, docs = await asyncio.gather(
        db["recipes"].count_documents(query),
        db["recipes"].find(query, _LIST_PROJ).skip(skip).limit(limit).to_list(limit),
    )

    return RecipeListResponse(
        results=[_to_card(doc) for doc in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{recipe_id}",
    response_model=RecipeDetail,
    summary="Detail resep; auto-simpan ke history jika ada JWT",
)
async def get_recipe(
    recipe_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    try:
        oid = ObjectId(recipe_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    doc = await db["recipes"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    if current_user:
        try:
            await db["history"].insert_one({
                "user_id": current_user["_id"],
                "recipe_id": oid,
                "viewed_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass  # history failure must not break the main response

    return _to_detail(doc)
