import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.auth.models import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    user_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID | None
    tenant_name: str | None


class MeRead(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID | None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    tenant_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID | None
    is_active: bool
    created_at: datetime


class DirectoryUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: UserRole
