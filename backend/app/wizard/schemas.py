import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.wizard.models import WizardTaskStatus


class TaskTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    requires_evidence: bool
    order_index: int


class PhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    code: str
    name: str
    objective: str


class PhaseWithTemplatesRead(PhaseRead):
    templates: list[TaskTemplateRead] = []


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phase_id: uuid.UUID
    template_id: uuid.UUID | None
    title: str
    description: str | None
    requires_evidence: bool
    owner: str | None
    due_date: date | None
    status: WizardTaskStatus
    evidence_document_id: uuid.UUID | None
    completed_at: datetime | None
    created_at: datetime


class TaskCreate(BaseModel):
    phase_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    requires_evidence: bool = True
    owner: str | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    owner: str | None = None
    due_date: date | None = None
    evidence_document_id: uuid.UUID | None = None


class PhaseProgress(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phase: PhaseRead
    status: str  # "locked" | "current" | "complete"
    tasks: list[TaskRead]
    done_count: int
    total_count: int


class InstantiateResult(BaseModel):
    created: int
