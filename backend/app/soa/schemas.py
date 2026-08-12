import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.soa.models import ImplementationStatus


class DomainSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class ControlSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    evidence_guidance: str | None
    domain: DomainSummary


class SoaEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    control: ControlSummary
    is_applicable: bool
    justification: str | None
    implementation_status: ImplementationStatus
    owner_user_id: uuid.UUID | None
    evidence_document_id: uuid.UUID | None
    notes: str | None
    updated_at: datetime


class SoaEntryUpdate(BaseModel):
    is_applicable: bool | None = None
    justification: str | None = None
    implementation_status: ImplementationStatus | None = None
    owner_user_id: uuid.UUID | None = None
    evidence_document_id: uuid.UUID | None = None
    notes: str | None = None


class SoaSummary(BaseModel):
    total: int
    applicable: int
    excluded: int
    implemented: int
    in_progress: int
    not_started: int


class InstantiateResult(BaseModel):
    created: int
