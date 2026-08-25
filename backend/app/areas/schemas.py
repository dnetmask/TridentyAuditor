import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    manager_user_id: uuid.UUID | None = None


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    manager_user_id: uuid.UUID | None = None


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    manager_user_id: uuid.UUID | None
    created_at: datetime
