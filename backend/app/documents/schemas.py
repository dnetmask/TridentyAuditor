import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.documents.models import DocumentOrigin, DocumentStatus

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
    controls: list[DocumentControlRead] = []
    created_at: datetime


class DocumentDetailRead(DocumentRead):
    versions: list[DocumentVersionRead] = []


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
