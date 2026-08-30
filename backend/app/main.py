import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import ASCENDING

from app.core.config import settings
from app.core.database import mongodb
from app.routes import auth, bookmarks, evaluation, history, ratings, recipes, recommendations
from app.services.recommendation_engine import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Connect to MongoDB
    await mongodb.connect()

    # 2. Ensure indexes
    await mongodb.db["users"].create_index(
        [("email", ASCENDING)], unique=True, background=True
    )
    await mongodb.db["ratings"].create_index(
        [("user_id", ASCENDING), ("recipe_id", ASCENDING)], unique=True, background=True
    )
    await mongodb.db["bookmarks"].create_index(
        [("user_id", ASCENDING), ("recipe_id", ASCENDING)], unique=True, background=True
    )
    await mongodb.db["history"].create_index(
        [("user_id", ASCENDING), ("viewed_at", ASCENDING)], background=True
    )

    # 3. Initialise AI engine (load model + vectors)
    await engine.initialize(mongodb.db)

    yield

    await mongodb.close()


app = FastAPI(
    title="Smart Recipe API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(recipes.router)
app.include_router(recommendations.router)
app.include_router(ratings.router)
app.include_router(bookmarks.router)
app.include_router(history.router)
app.include_router(evaluation.router)


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "database": settings.database_name,
        "engine_ready": engine.is_ready,
        "vectors_loaded": len(engine.recipe_ids) if engine.is_ready else 0,
    }
