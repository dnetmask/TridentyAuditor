import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.documents.models import DocumentStatus


class DocumentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=50)
    control_id: uuid.UUID | None = None
    retention_months: int | None = Field(default=None, ge=1)
    storage_ref: str = Field(min_length=1, max_length=500)
    change_summary: str | None = None


class NewVersionCreate(BaseModel):
    storage_ref: str = Field(min_length=1, max_length=500)
    change_summary: str | None = None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    status: DocumentStatus
    storage_ref: str
    change_summary: str | None
    created_by: str
    approved_by: str | None
    created_at: datetime
    approved_at: datetime | None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    document_type: str
    control_id: uuid.UUID | None
    retention_months: int | None
    created_at: datetime


class DocumentDetailRead(DocumentRead):
    versions: list[DocumentVersionRead] = []
