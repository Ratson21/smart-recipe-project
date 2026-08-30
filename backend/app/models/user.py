from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password minimal 6 karakter")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama lengkap tidak boleh kosong")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
