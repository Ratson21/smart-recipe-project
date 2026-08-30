from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.core.config import settings

_ALGORITHM = "HS256"


# ── Password ──────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────

def create_access_token(payload: dict[str, Any]) -> str:
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    data["exp"] = expire
    return jwt.encode(data, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
