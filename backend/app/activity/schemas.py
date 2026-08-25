import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_email: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    detail: str | None
    ip_address: str | None
    created_at: datetime
