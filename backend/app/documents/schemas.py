import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.documents.models import (
    ApprovalStep,
    DispositionAction,
    DocumentOrigin,
    DocumentStatus,
)

# Nota: no hay DocumentCreate/NewVersionCreate — ambos endpoints reciben
# multipart/form-data (Form + UploadFile) porque exigen adjuntar un archivo,
# no un body JSON. Ver documents/router.py.


class DocumentControlRead(BaseModel):
    """Chip de control enlazado — lo mínimo para mostrarlo y filtrarlo."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class DocumentAreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    # El frontend lo usa para saber si el usuario actual es el gerente que
    # puede firmar el paso "gerente de área" de la aprobación multinivel.
    manager_user_id: uuid.UUID | None = None


class DocumentApprovalRead(BaseModel):
    """Una firma de la aprobación multinivel, con su sello."""

    model_config = ConfigDict(from_attributes=True)

    step: ApprovalStep
    signed_by: str
    signed_at: datetime
    file_sha256: str | None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    status: DocumentStatus
    original_filename: str | None
    content_type: str | None
    file_size: int | None
    file_sha256: str | None
    change_summary: str | None
    created_by: str
    approved_by: str | None
    rejected_by: str | None
    rejected_at: datetime | None
    rejection_reason: str | None
    approvals: list[DocumentApprovalRead] = []
    created_at: datetime
    approved_at: datetime | None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    document_type: str
    retention_months: int | None
    area: DocumentAreaRead | None
    implementation_date: date | None
    review_frequency_months: int | None
    next_review_date: date | None
    origin: DocumentOrigin
    external_source: str | None
    retired_at: datetime | None
    retired_by: str | None
    retirement_reason: str | None
    # --- Retención / disposición (Fase 5) ---
    legal_hold: bool = False
    disposed_at: datetime | None = None
    disposed_by: str | None = None
    disposition_action: DispositionAction | None = None
    disposition_notes: str | None = None
    controls: list[DocumentControlRead] = []
    created_at: datetime


class DocumentDetailRead(DocumentRead):
    versions: list[DocumentVersionRead] = []
    # Fecha calculada en que cumple retención y puede disponerse (o null).
    disposition_date: date | None = None


class AcknowledgmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_id: uuid.UUID
    user_id: uuid.UUID
    assigned_by: str
    assigned_at: datetime
    acknowledged_at: datetime | None


class AcknowledgmentSummary(BaseModel):
    total: int
    acknowledged: int
    pending: int
    entries: list[AcknowledgmentRead] = []


class PublishRequest(BaseModel):
    user_ids: list[uuid.UUID] = Field(min_length=1)


class DispositionRequest(BaseModel):
    action: DispositionAction
    notes: str = Field(min_length=1)


class LegalHoldRequest(BaseModel):
    hold: bool


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    document_type: str
    original_filename: str | None
    content_type: str | None
    file_size: int | None
    created_by: str
    created_at: datetime


class DocumentUpdate(BaseModel):
    """PATCH de metadatos — el ``code`` es identidad y no se edita.

    ``control_ids`` reemplaza el conjunto completo de enlaces (enviar ``[]``
    los limpia; no enviarlo los deja como están), igual que en MOD·RSK.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    document_type: str | None = Field(default=None, min_length=1, max_length=50)
    retention_months: int | None = Field(default=None, ge=1)
    area_id: uuid.UUID | None = None
    implementation_date: date | None = None
    review_frequency_months: int | None = Field(default=None, ge=1)
    next_review_date: date | None = None
    origin: DocumentOrigin | None = None
    external_source: str | None = Field(default=None, max_length=255)
    control_ids: list[uuid.UUID] | None = None


class DocumentRetireRequest(BaseModel):
    reason: str = Field(min_length=1)


class VersionRejectRequest(BaseModel):
    reason: str = Field(min_length=1)


class NextCodeRead(BaseModel):
    code: str


class ApprovalSealRead(BaseModel):
    step: str
    signed_by: str
    signed_at: datetime
    file_sha256: str | None
    matches_current: bool | None


class VersionIntegrityRead(BaseModel):
    version_number: int
    algorithm: str
    expected_sha256: str | None
    actual_sha256: str | None
    has_hash: bool
    file_present: bool
    verified: bool
    approvals: list[ApprovalSealRead]
