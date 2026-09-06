import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProcessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    order_index: int = 0
    document_ids: list[uuid.UUID] = []


class ProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    order_index: int | None = None
    # Reemplaza el conjunto completo de documentos vinculados (como en MOD·RSK).
    document_ids: list[uuid.UUID] | None = None


class ProcessDocumentRead(BaseModel):
    """Documento colgado de un proceso — lo mínimo para el árbol."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str


class ProcessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    owner_user_id: uuid.UUID | None
    order_index: int
    created_at: datetime


class ProcessNode(ProcessRead):
    """Nodo del árbol: proceso + sus documentos + subprocesos anidados."""

    documents: list[ProcessDocumentRead] = []
    children: list["ProcessNode"] = []
    document_count: int = 0  # documentos propios + de los subprocesos
