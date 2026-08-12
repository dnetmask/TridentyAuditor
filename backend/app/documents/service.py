import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.documents.models import Document, DocumentStatus, DocumentVersion


class DocumentError(Exception):
    """Base error for MOD·DOC business-rule violations (mapped to HTTP 409/404)."""


class DocumentNotFound(DocumentError):
    pass


class VersionNotFound(DocumentError):
    pass


class InvalidTransition(DocumentError):
    pass


def has_approved_version(db: Session, tenant_id: str, document_id: uuid.UUID) -> bool:
    stmt = select(DocumentVersion.id).where(
        DocumentVersion.tenant_id == tenant_id,
        DocumentVersion.document_id == document_id,
        DocumentVersion.status == DocumentStatus.APPROVED,
    )
    return db.scalars(stmt).first() is not None


def approved_document_ids(db: Session, tenant_id: str) -> set[uuid.UUID]:
    """IDs de todos los documentos del tenant con al menos una versión aprobada.

    Pensado para chequear "¿esta evidencia es real?" contra muchos registros
    a la vez (ej. las 93 entradas del SoA) sin una consulta por registro.
    """
    stmt = select(DocumentVersion.document_id).where(
        DocumentVersion.tenant_id == tenant_id,
        DocumentVersion.status == DocumentStatus.APPROVED,
    ).distinct()
    return set(db.scalars(stmt))


def _get_document(db: Session, tenant_id: str, document_id: uuid.UUID) -> Document:
    stmt = (
        select(Document)
        .where(Document.id == document_id, Document.tenant_id == tenant_id)
        .options(selectinload(Document.versions))
    )
    document = db.scalars(stmt).first()
    if document is None:
        raise DocumentNotFound(str(document_id))
    return document


def create_document(
    db: Session,
    tenant_id: str,
    *,
    code: str,
    title: str,
    document_type: str,
    control_id: uuid.UUID | None,
    retention_months: int | None,
    storage_ref: str,
    created_by: str,
    change_summary: str | None,
) -> Document:
    document = Document(
        tenant_id=tenant_id,
        code=code,
        title=title,
        document_type=document_type,
        control_id=control_id,
        retention_months=retention_months,
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(
        tenant_id=tenant_id,
        document_id=document.id,
        version_number=1,
        status=DocumentStatus.DRAFT,
        storage_ref=storage_ref,
        created_by=created_by,
        change_summary=change_summary,
    )
    db.add(version)
    db.flush()
    db.refresh(document)
    return document


def list_documents(db: Session, tenant_id: str) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .options(selectinload(Document.versions))
        .order_by(Document.code)
    )
    return list(db.scalars(stmt))


def get_document(db: Session, tenant_id: str, document_id: uuid.UUID) -> Document:
    return _get_document(db, tenant_id, document_id)


def create_new_version(
    db: Session,
    tenant_id: str,
    document_id: uuid.UUID,
    *,
    storage_ref: str,
    created_by: str,
    change_summary: str | None,
) -> DocumentVersion:
    document = _get_document(db, tenant_id, document_id)
    if any(v.status in (DocumentStatus.DRAFT, DocumentStatus.IN_REVIEW) for v in document.versions):
        raise InvalidTransition(
            "Ya existe una versión en borrador o revisión; ciérrela antes de abrir otra"
        )
    next_number = max((v.version_number for v in document.versions), default=0) + 1
    version = DocumentVersion(
        tenant_id=tenant_id,
        document_id=document.id,
        version_number=next_number,
        status=DocumentStatus.DRAFT,
        storage_ref=storage_ref,
        created_by=created_by,
        change_summary=change_summary,
    )
    db.add(version)
    db.flush()
    return version


def _get_version(db: Session, tenant_id: str, document_id: uuid.UUID, version_number: int) -> DocumentVersion:
    stmt = select(DocumentVersion).where(
        DocumentVersion.tenant_id == tenant_id,
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == version_number,
    )
    version = db.scalars(stmt).first()
    if version is None:
        raise VersionNotFound(f"{document_id}/{version_number}")
    return version


def submit_for_review(db: Session, tenant_id: str, document_id: uuid.UUID, version_number: int) -> DocumentVersion:
    version = _get_version(db, tenant_id, document_id, version_number)
    if version.status != DocumentStatus.DRAFT:
        raise InvalidTransition(f"No se puede enviar a revisión desde estado '{version.status.value}'")
    version.status = DocumentStatus.IN_REVIEW
    db.flush()
    return version


def reject_version(db: Session, tenant_id: str, document_id: uuid.UUID, version_number: int) -> DocumentVersion:
    version = _get_version(db, tenant_id, document_id, version_number)
    if version.status != DocumentStatus.IN_REVIEW:
        raise InvalidTransition(f"No se puede rechazar desde estado '{version.status.value}'")
    version.status = DocumentStatus.DRAFT
    db.flush()
    return version


def approve_version(
    db: Session, tenant_id: str, document_id: uuid.UUID, version_number: int, approved_by: str
) -> DocumentVersion:
    version = _get_version(db, tenant_id, document_id, version_number)
    if version.status != DocumentStatus.IN_REVIEW:
        raise InvalidTransition(f"No se puede aprobar desde estado '{version.status.value}'")

    document = _get_document(db, tenant_id, document_id)
    for other in document.versions:
        if other.id != version.id and other.status == DocumentStatus.APPROVED:
            other.status = DocumentStatus.OBSOLETE

    version.status = DocumentStatus.APPROVED
    version.approved_by = approved_by
    version.approved_at = datetime.now(UTC)
    db.flush()
    return version
