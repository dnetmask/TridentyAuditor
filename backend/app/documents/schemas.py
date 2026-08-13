import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.documents.models import DocumentStatus

# Nota: no hay DocumentCreate/NewVersionCreate — ambos endpoints reciben
# multipart/form-data (Form + UploadFile) porque exigen adjuntar un archivo,
# no un body JSON. Ver documents/router.py.


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    status: DocumentStatus
    original_filename: str | None
    content_type: str | None
    file_size: int | None
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
