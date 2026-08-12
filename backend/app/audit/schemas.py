import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.audit.models import AuditStatus, FindingClassification, FindingStatus


class DomainSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class ControlSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class AuditProgramCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    scope: str | None = None
    domain_id: uuid.UUID | None = None
    auditor_user_id: uuid.UUID | None = None
    planned_date: date | None = None


class AuditProgramUpdate(BaseModel):
    title: str | None = None
    scope: str | None = None
    domain_id: uuid.UUID | None = None
    auditor_user_id: uuid.UUID | None = None
    planned_date: date | None = None
    executed_date: date | None = None
    status: AuditStatus | None = None


class AuditProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    scope: str | None
    domain: DomainSummary | None
    auditor_user_id: uuid.UUID | None
    planned_date: date | None
    executed_date: date | None
    status: AuditStatus
    created_at: datetime


class AuditFindingCreate(BaseModel):
    audit_id: uuid.UUID
    control_id: uuid.UUID | None = None
    classification: FindingClassification
    description: str = Field(min_length=1)
    root_cause: str | None = None
    corrective_action: str | None = None
    owner_user_id: uuid.UUID | None = None
    due_date: date | None = None


class AuditFindingUpdate(BaseModel):
    control_id: uuid.UUID | None = None
    classification: FindingClassification | None = None
    description: str | None = None
    root_cause: str | None = None
    corrective_action: str | None = None
    owner_user_id: uuid.UUID | None = None
    due_date: date | None = None
    status: FindingStatus | None = None
    evidence_document_id: uuid.UUID | None = None


class AuditFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    audit_id: uuid.UUID
    control: ControlSummary | None
    classification: FindingClassification
    description: str
    root_cause: str | None
    corrective_action: str | None
    owner_user_id: uuid.UUID | None
    due_date: date | None
    status: FindingStatus
    evidence_document_id: uuid.UUID | None
    closed_at: datetime | None
    created_at: datetime


class AuditSummary(BaseModel):
    total_programs: int
    total_findings: int
    open_findings: int
    in_progress_findings: int
    closed_findings: int
    major_nc: int
    minor_nc: int
