from datetime import datetime

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.recipe import RecipeCard

router = APIRouter(prefix="/api/v1/history", tags=["history"])

_HISTORY_LIMIT = 50


class HistoryItem(BaseModel):
    recipe: RecipeCard
    viewed_at: datetime


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


@router.get(
    "",
    response_model=list[HistoryItem],
    summary="50 resep terbaru yang dilihat user",
)
async def get_history(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    history_docs = await db["history"].find(
        {"user_id": current_user["_id"]}
    ).sort("viewed_at", -1).limit(_HISTORY_LIMIT).to_list(_HISTORY_LIMIT)

    if not history_docs:
        return []

    recipe_oids = [h["recipe_id"] for h in history_docs]
    recipe_docs = await db["recipes"].find(
        {"_id": {"$in": recipe_oids}}, {"ingredients_raw": 0, "steps": 0}
    ).to_list(length=None)
    recipe_map = {str(d["_id"]): d for d in recipe_docs}

    return [
        HistoryItem(recipe=_to_card(recipe_map[str(h["recipe_id"])]), viewed_at=h["viewed_at"])
        for h in history_docs
        if str(h["recipe_id"]) in recipe_map
    ]
