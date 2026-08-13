"""Binarios de MOD·DOC en disco local (ver Settings.documents_storage_dir).

``storage_ref`` se construye siempre a partir de UUIDs generados por el
propio backend (tenant_id/document_id/version_id) — nunca a partir de un
nombre de archivo dado por el usuario — así que no hay superficie de path
traversal que sanear. El nombre original que sube el usuario se guarda solo
como metadato (``DocumentVersion.original_filename``) para el encabezado
``Content-Disposition`` en la descarga.
"""

import uuid
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def _root() -> Path:
    return Path(settings.documents_storage_dir)


def build_storage_ref(tenant_id: uuid.UUID | str, document_id: uuid.UUID, version_id: uuid.UUID) -> str:
    return f"{tenant_id}/{document_id}/{version_id}"


def save(storage_ref: str, content: bytes) -> None:
    path = _root() / storage_ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def path_for(storage_ref: str) -> Path:
    return _root() / storage_ref


def exists(storage_ref: str) -> bool:
    return path_for(storage_ref).is_file()


def delete(storage_ref: str) -> None:
    path_for(storage_ref).unlink(missing_ok=True)
