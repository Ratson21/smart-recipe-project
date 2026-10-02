from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# Helpers

def _to_user_response(doc: dict) -> UserResponse:
    return UserResponse(
        id=str(doc["_id"]),
        email=doc["email"],
        full_name=doc["full_name"],
        created_at=doc["created_at"],
    )


# Endpoints

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrasi akun baru",
)
async def register(
    body: UserRegister,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if await db["users"].find_one({"email": body.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar",
        )

    doc = {
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "full_name": body.full_name,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db["users"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_user_response(doc)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login dan dapatkan JWT",
)
async def login(
    body: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await db["users"].find_one({"email": body.email})
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
        )

    token = create_access_token({"sub": str(user["_id"]), "email": user["email"]})
    return TokenResponse(access_token=token, user=_to_user_response(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Info user dari JWT",
)
async def me(user: dict = Depends(get_current_user)):
    return _to_user_response(user)
