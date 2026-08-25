import calendar
import hashlib
import re
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.documents import storage
from app.documents.models import (
    Document,
    DocumentControlLink,
    DocumentOrigin,
    DocumentStatus,
    DocumentVersion,
)
from app.frameworks.models import Control


class DocumentError(Exception):
    """Base error for MOD·DOC business-rule violations (mapped to HTTP 409/404)."""


class DocumentNotFound(DocumentError):
    pass


class VersionNotFound(DocumentError):
    pass


class InvalidTransition(DocumentError):
    pass


class UnknownControl(DocumentError):
    """Algún control_id del enlace no existe en el motor de frameworks."""


class FileIntegrityError(DocumentError):
    """El binario en disco no coincide con el SHA-256 registrado al subir.

    Si esto salta, alguien (o algo) tocó el archivo por fuera de la
    plataforma — servirlo como si nada convertiría una evidencia adulterada
    en evidencia 'oficial'.
    """


class FileMissing(DocumentError):
    """El registro existe pero el binario no está en el almacenamiento.

    Solo debería darse en versiones creadas antes de que MOD·DOC exigiera
    subir un archivo (storage_ref manual tipo ``s3://...`` que nunca tuvo un
    binario real detrás) o si alguien borró el volumen de almacenamiento a
    mano.
    """


# Prefijo del consecutivo sugerido, por tipo de documento.
CODE_PREFIXES = {
    "policy": "POL",
    "procedure": "PRC",
    "record": "REG",
    "other": "DOC",
}


def has_approved_version(db: Session, tenant_id: str, document_id: uuid.UUID) -> bool:
    """¿Tiene versión aprobada Y sigue vigente (no derogado)?

    Un documento derogado deja de contar como evidencia válida para wizard,
    auditoría e indicador de cumplimiento — retirarlo es exactamente decir
    "esto ya no respalda nada".
    """
    stmt = (
        select(DocumentVersion.id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(
            DocumentVersion.tenant_id == tenant_id,
            DocumentVersion.document_id == document_id,
            DocumentVersion.status == DocumentStatus.APPROVED,
            Document.retired_at.is_(None),
        )
    )
    return db.scalars(stmt).first() is not None


def approved_document_ids(db: Session, tenant_id: str) -> set[uuid.UUID]:
    """IDs de todos los documentos VIGENTES del tenant con versión aprobada.

    Pensado para chequear "¿esta evidencia es real?" contra muchos registros
    a la vez (ej. las entradas del SoA) sin una consulta por registro. Los
    documentos derogados quedan fuera (ver ``has_approved_version``).
    """
    stmt = (
        select(DocumentVersion.document_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(
            DocumentVersion.tenant_id == tenant_id,
            DocumentVersion.status == DocumentStatus.APPROVED,
            Document.retired_at.is_(None),
        )
        .distinct()
    )
    return set(db.scalars(stmt))


def _document_query_options():
    return (
        selectinload(Document.versions),
        selectinload(Document.control_links).selectinload(DocumentControlLink.control),
        selectinload(Document.area),
    )


def _get_document(db: Session, tenant_id: str, document_id: uuid.UUID) -> Document:
    stmt = (
        select(Document)
        .where(Document.id == document_id, Document.tenant_id == tenant_id)
        .options(*_document_query_options())
    )
    document = db.scalars(stmt).first()
    if document is None:
        raise DocumentNotFound(str(document_id))
    return document


def _set_control_links(db: Session, document: Document, control_ids: list[uuid.UUID]) -> None:
    """Reemplaza el conjunto completo de enlaces documento↔control.

    Mismo contrato que en MOD·RSK: la lista que llega ES el estado final —
    no hay agregar-uno/quitar-uno incremental.
    """
    unique_ids = list(dict.fromkeys(control_ids))
    if unique_ids:
        found = set(db.scalars(select(Control.id).where(Control.id.in_(unique_ids))))
        missing = [str(cid) for cid in unique_ids if cid not in found]
        if missing:
            raise UnknownControl(", ".join(missing))
    document.control_links.clear()
    db.flush()
    for control_id in unique_ids:
        db.add(
            DocumentControlLink(
                tenant_id=document.tenant_id, document_id=document.id, control_id=control_id
            )
        )
    db.flush()


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def suggest_next_code(db: Session, tenant_id: str, document_type: str) -> str:
    """Consecutivo sugerido por tipo (POL-001, PRC-014, …), editable por el usuario.

    Escanea los códigos existentes del tenant que sigan el patrón del
    prefijo y propone el siguiente. Un código a mano fuera del patrón no
    estorba: simplemente no participa del consecutivo.
    """
    prefix = CODE_PREFIXES.get(document_type, "DOC")
    stmt = select(Document.code).where(
        Document.tenant_id == tenant_id, Document.code.like(f"{prefix}-%")
    )
    pattern = re.compile(rf"^{prefix}-(\d+)$")
    highest = 0
    for code in db.scalars(stmt):
        match = pattern.match(code)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}-{highest + 1:03d}"


def create_document(
    db: Session,
    tenant_id: str,
    *,
    code: str,
    title: str,
    document_type: str,
    retention_months: int | None,
    created_by: str,
    change_summary: str | None,
    file_content: bytes,
    original_filename: str,
    content_type: str | None,
    area_id: uuid.UUID | None = None,
    implementation_date: date | None = None,
    review_frequency_months: int | None = None,
    next_review_date: date | None = None,
    origin: DocumentOrigin = DocumentOrigin.INTERNAL,
    external_source: str | None = None,
    control_ids: list[uuid.UUID] | None = None,
) -> Document:
    document = Document(
        tenant_id=tenant_id,
        code=code,
        title=title,
        document_type=document_type,
        retention_months=retention_months,
        area_id=area_id,
        implementation_date=implementation_date,
        review_frequency_months=review_frequency_months,
        next_review_date=next_review_date,
        origin=origin,
        external_source=external_source if origin == DocumentOrigin.EXTERNAL else None,
    )
    db.add(document)
    # Flush primero para que un código duplicado falle (IntegrityError, 409)
    # antes de escribir nada a disco — evita dejar un archivo huérfano.
    db.flush()

    if control_ids:
        _set_control_links(db, document, control_ids)

    version_id = uuid.uuid4()
    storage_ref = storage.build_storage_ref(tenant_id, document.id, version_id)
    storage.save(storage_ref, file_content)

    version = DocumentVersion(
        id=version_id,
        tenant_id=tenant_id,
        document_id=document.id,
        version_number=1,
        status=DocumentStatus.DRAFT,
        storage_ref=storage_ref,
        original_filename=original_filename,
        content_type=content_type,
        file_size=len(file_content),
        file_sha256=_file_sha256(file_content),
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
        .options(*_document_query_options())
        .order_by(Document.code)
    )
    return list(db.scalars(stmt))


def get_document(db: Session, tenant_id: str, document_id: uuid.UUID) -> Document:
    return _get_document(db, tenant_id, document_id)


_UNSET = object()


def update_document(
    db: Session,
    tenant_id: str,
    document_id: uuid.UUID,
    *,
    title: str | None = None,
    document_type: str | None = None,
    retention_months: int | None | object = _UNSET,
    area_id: uuid.UUID | None | object = _UNSET,
    implementation_date: date | None | object = _UNSET,
    review_frequency_months: int | None | object = _UNSET,
    next_review_date: date | None | object = _UNSET,
    origin: DocumentOrigin | None = None,
    external_source: str | None | object = _UNSET,
    control_ids: list[uuid.UUID] | None = None,
) -> Document:
    """Corrige metadatos sin tocar versiones ni flujo de aprobación.

    El ``code`` es identidad del documento (aparece en pies de página,
    referencias cruzadas y el consecutivo) — no se edita por aquí.
    """
    document = _get_document(db, tenant_id, document_id)
    if document.retired_at is not None:
        raise InvalidTransition("Un documento derogado no se edita; queda como registro histórico")

    if title is not None:
        document.title = title
    if document_type is not None:
        document.document_type = document_type
    if retention_months is not _UNSET:
        document.retention_months = retention_months
    if area_id is not _UNSET:
        document.area_id = area_id
    if implementation_date is not _UNSET:
        document.implementation_date = implementation_date
    if review_frequency_months is not _UNSET:
        document.review_frequency_months = review_frequency_months
    if next_review_date is not _UNSET:
        document.next_review_date = next_review_date
    if origin is not None:
        document.origin = origin
    if external_source is not _UNSET:
        document.external_source = external_source
    if document.origin != DocumentOrigin.EXTERNAL:
        document.external_source = None
    if control_ids is not None:
        _set_control_links(db, document, control_ids)

    db.flush()
    db.refresh(document)
    return document


def retire_document(
    db: Session, tenant_id: str, document_id: uuid.UUID, *, reason: str, retired_by: str
) -> Document:
    """Derogación formal: el documento completo deja de estar vigente.

    No borra nada — el historial de versiones queda intacto como registro —
    pero el documento deja de contar como evidencia aprobada en wizard,
    auditoría e indicador de cumplimiento, y no admite más ediciones ni
    versiones nuevas.
    """
    document = _get_document(db, tenant_id, document_id)
    if document.retired_at is not None:
        raise InvalidTransition("El documento ya está derogado")
    document.retired_at = datetime.now(UTC)
    document.retired_by = retired_by
    document.retirement_reason = reason
    db.flush()
    db.refresh(document)
    return document


def create_new_version(
    db: Session,
    tenant_id: str,
    document_id: uuid.UUID,
    *,
    created_by: str,
    change_summary: str,
    file_content: bytes,
    original_filename: str,
    content_type: str | None,
) -> DocumentVersion:
    document = _get_document(db, tenant_id, document_id)
    if document.retired_at is not None:
        raise InvalidTransition("Un documento derogado no admite versiones nuevas")
    if any(v.status in (DocumentStatus.DRAFT, DocumentStatus.IN_REVIEW) for v in document.versions):
        raise InvalidTransition(
            "Ya existe una versión en borrador o revisión; ciérrela antes de abrir otra"
        )
    next_number = max((v.version_number for v in document.versions), default=0) + 1

    version_id = uuid.uuid4()
    storage_ref = storage.build_storage_ref(tenant_id, document.id, version_id)
    storage.save(storage_ref, file_content)

    version = DocumentVersion(
        id=version_id,
        tenant_id=tenant_id,
        document_id=document.id,
        version_number=next_number,
        status=DocumentStatus.DRAFT,
        storage_ref=storage_ref,
        original_filename=original_filename,
        content_type=content_type,
        file_size=len(file_content),
        file_sha256=_file_sha256(file_content),
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


def reject_version(
    db: Session,
    tenant_id: str,
    document_id: uuid.UUID,
    version_number: int,
    *,
    reason: str,
    rejected_by: str,
) -> DocumentVersion:
    version = _get_version(db, tenant_id, document_id, version_number)
    if version.status != DocumentStatus.IN_REVIEW:
        raise InvalidTransition(f"No se puede rechazar desde estado '{version.status.value}'")
    version.status = DocumentStatus.DRAFT
    version.rejected_by = rejected_by
    version.rejected_at = datetime.now(UTC)
    version.rejection_reason = reason
    db.flush()
    return version


def get_version_file(
    db: Session, tenant_id: str, document_id: uuid.UUID, version_number: int
) -> tuple[DocumentVersion, Path]:
    version = _get_version(db, tenant_id, document_id, version_number)
    path = storage.path_for(version.storage_ref)
    if not path.is_file():
        raise FileMissing(f"{document_id}/{version_number}")
    # Verificación de integridad al servir: el hash registrado al subir debe
    # coincidir con lo que hay en disco. Las versiones anteriores a la Fase 1
    # no tienen hash — se sirven sin verificar, no hay contra qué comparar.
    if version.file_sha256 is not None:
        actual = _file_sha256(path.read_bytes())
        if actual != version.file_sha256:
            raise FileIntegrityError(f"{document_id}/{version_number}")
    return version, path


def approve_version(
    db: Session, tenant_id: str, document_id: uuid.UUID, version_number: int, approved_by: str
) -> DocumentVersion:
    version = _get_version(db, tenant_id, document_id, version_number)
    if version.status != DocumentStatus.IN_REVIEW:
        raise InvalidTransition(f"No se puede aprobar desde estado '{version.status.value}'")

    document = _get_document(db, tenant_id, document_id)
    if document.retired_at is not None:
        raise InvalidTransition("Un documento derogado no admite aprobaciones")
    for other in document.versions:
        if other.id != version.id and other.status == DocumentStatus.APPROVED:
            other.status = DocumentStatus.OBSOLETE

    version.status = DocumentStatus.APPROVED
    version.approved_by = approved_by
    version.approved_at = datetime.now(UTC)
    # Revisión periódica programada: aprobar arranca (o reinicia) el reloj.
    if document.review_frequency_months:
        document.next_review_date = _add_months(date.today(), document.review_frequency_months)
    db.flush()
    return version
