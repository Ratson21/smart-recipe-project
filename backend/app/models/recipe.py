from pydantic import BaseModel, ConfigDict


class RecipeBase(BaseModel):
    """Fields shared by list and detail responses."""
    id: str
    title: str
    category: str
    total_ingredients: int
    total_steps: int
    estimated_time_minutes: int
    difficulty_level: str
    average_rating: float
    total_reviews: int

    model_config = ConfigDict(from_attributes=True)


class RecipeCard(RecipeBase):
    """Lightweight schema for list endpoint (no raw text blobs)."""
    ingredients_cleaned: str


class RecipeDetail(RecipeBase):
    """Full schema for detail endpoint."""
    ingredients_raw: str
    ingredients_cleaned: str
    steps: str


class RecipeListResponse(BaseModel):
    results: list[RecipeCard]
    total: int
    skip: int
    limit: int
