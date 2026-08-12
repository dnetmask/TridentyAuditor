import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.tenants.models import IsolationTier


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    isolation_tier: IsolationTier = IsolationTier.POOLED


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    isolation_tier: IsolationTier
    created_at: datetime
