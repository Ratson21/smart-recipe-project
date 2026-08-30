"""Shared FastAPI dependencies - auth, optional auth."""

from typing import Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.security import decode_access_token

_bearer          = HTTPBearer()
_optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Require valid JWT - raises 401 if missing or invalid."""
    payload = decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")

    user = await db["users"].find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan")
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Optional[dict]:
    """Return user dict if JWT is present and valid, otherwise None (no error)."""
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if not user_id:
            return None
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        return user
    except Exception:
        return None
