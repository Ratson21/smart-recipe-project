from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user

router = APIRouter(prefix="/api/v1/ratings", tags=["ratings"])


class RatingRequest(BaseModel):
    recipe_id: str
    rating_score: int = Field(..., ge=1, le=5)


class RatingResponse(BaseModel):
    recipe_id: str
    rating_score: int
    created_at: datetime


async def _refresh_recipe_stats(db: AsyncIOMotorDatabase, recipe_oid: ObjectId) -> None:
    """Recompute average_rating and total_reviews from ratings collection."""
    pipeline = [
        {"$match": {"recipe_id": recipe_oid}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating_score"}, "count": {"$sum": 1}}},
    ]
    docs = await db["ratings"].aggregate(pipeline).to_list(length=1)
    if docs:
        avg = round(docs[0]["avg"], 2)
        count = docs[0]["count"]
    else:
        avg, count = 0.0, 0
    await db["recipes"].update_one(
        {"_id": recipe_oid},
        {"$set": {"average_rating": avg, "total_reviews": count}},
    )


@router.post(
    "",
    response_model=RatingResponse,
    status_code=status.HTTP_200_OK,
    summary="Simpan atau update rating user untuk sebuah resep (upsert 1-5)",
)
async def upsert_rating(
    body: RatingRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        recipe_oid = ObjectId(body.recipe_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    if not await db["recipes"].find_one({"_id": recipe_oid}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    now = datetime.now(timezone.utc)
    await db["ratings"].update_one(
        {"user_id": current_user["_id"], "recipe_id": recipe_oid},
        {"$set": {"rating_score": body.rating_score, "created_at": now}},
        upsert=True,
    )
    await _refresh_recipe_stats(db, recipe_oid)

    return RatingResponse(recipe_id=body.recipe_id, rating_score=body.rating_score, created_at=now)


@router.get(
    "/recipe/{recipe_id}",
    response_model=Optional[RatingResponse],
    summary="Rating user saat ini untuk resep tertentu (null jika belum rating atau tidak login)",
)
async def get_user_rating(
    recipe_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    if not current_user:
        return None

    try:
        recipe_oid = ObjectId(recipe_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    doc = await db["ratings"].find_one(
        {"user_id": current_user["_id"], "recipe_id": recipe_oid}
    )
    if not doc:
        return None

    return RatingResponse(
        recipe_id=recipe_id,
        rating_score=doc["rating_score"],
        created_at=doc["created_at"],
    )
