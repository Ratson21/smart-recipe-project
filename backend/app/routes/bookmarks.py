from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.recipe import RecipeCard

router = APIRouter(prefix="/api/v1/bookmarks", tags=["bookmarks"])


class BookmarkRequest(BaseModel):
    recipe_id: str


class BookmarkResponse(BaseModel):
    recipe_id: str
    created_at: datetime


class BookmarkListItem(BaseModel):
    recipe: RecipeCard
    bookmarked_at: datetime


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


@router.post(
    "",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah bookmark resep (idempotent - tidak error jika sudah ada)",
)
async def add_bookmark(
    body: BookmarkRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        recipe_oid = ObjectId(body.recipe_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    if not await db["recipes"].find_one({"_id": recipe_oid}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resep tidak ditemukan")

    user_oid = current_user["_id"]
    existing = await db["bookmarks"].find_one({"user_id": user_oid, "recipe_id": recipe_oid})
    if existing:
        return BookmarkResponse(recipe_id=body.recipe_id, created_at=existing["created_at"])

    now = datetime.now(timezone.utc)
    await db["bookmarks"].insert_one({
        "user_id": user_oid,
        "recipe_id": recipe_oid,
        "created_at": now,
    })
    return BookmarkResponse(recipe_id=body.recipe_id, created_at=now)


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus bookmark",
)
async def remove_bookmark(
    recipe_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        recipe_oid = ObjectId(recipe_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark tidak ditemukan")

    result = await db["bookmarks"].delete_one(
        {"user_id": current_user["_id"], "recipe_id": recipe_oid}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark tidak ditemukan")


@router.get(
    "",
    response_model=list[BookmarkListItem],
    summary="List semua bookmark user, terbaru di atas",
)
async def list_bookmarks(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    bm_docs = await db["bookmarks"].find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1).to_list(length=None)

    if not bm_docs:
        return []

    recipe_oids = [bm["recipe_id"] for bm in bm_docs]
    recipe_docs = await db["recipes"].find(
        {"_id": {"$in": recipe_oids}}, {"ingredients_raw": 0, "steps": 0}
    ).to_list(length=None)
    recipe_map = {str(d["_id"]): d for d in recipe_docs}

    return [
        BookmarkListItem(recipe=_to_card(recipe_map[str(bm["recipe_id"])]), bookmarked_at=bm["created_at"])
        for bm in bm_docs
        if str(bm["recipe_id"]) in recipe_map
    ]
