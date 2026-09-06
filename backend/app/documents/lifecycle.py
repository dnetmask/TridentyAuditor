"""Fase 5 — acuse de recibo (leído y entendido) y retención/disposición.

Separado de ``documents/service.py`` (versionado y aprobación) porque es otro
eje del ciclo de vida: distribución controlada y fin de vida del documento.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.documents.models import (
    DispositionAction,
    Document,
    DocumentAcknowledgment,
    DocumentStatus,
    DocumentVersion,
)
from app.documents.service import DocumentError, DocumentNotFound, InvalidTransition


class UnknownUser(DocumentError):
    """Algún user_id no es un usuario activo del tenant."""


class NoApprovedVersion(DocumentError):
    """Solo se puede publicar (pedir acuse de) una versión aprobada."""


class AckNotFound(DocumentError):
    pass


def _get_document(db: Session, tenant_id: str, document_id: uuid.UUID) -> Document:
    document = db.scalars(
        select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
    ).first()
    if document is None:
        raise DocumentNotFound(str(document_id))
    return document


def _approved_version(document: Document) -> DocumentVersion | None:
    approved = [v for v in document.versions if v.status == DocumentStatus.APPROVED]
    return max(approved, key=lambda v: v.version_number) if approved else None


# --------------------------------------------------------------- acuse de recibo


def publish_for_acknowledgment(
    db: Session,
    tenant_id: str,
    document_id: uuid.UUID,
    *,
    user_ids: list[uuid.UUID],
    assigned_by: str,
) -> list[DocumentAcknowledgment]:
    """Pide acuse de recibo de la versión vigente a un conjunto de usuarios.

    Solo aplica a la versión APROBADA (no tiene sentido pedir "leído y
    entendido" de un borrador). Reasignar a alguien que ya tiene el acuse de
    esa versión es idempotente: no se duplica ni se borra su lectura.
    """
    document = _get_document(db, tenant_id, document_id)
    if document.retired_at is not None:
        raise InvalidTransition("Un documento derogado no se distribuye")
    version = _approved_version(document)
    if version is None:
        raise NoApprovedVersion(str(document_id))

    unique_ids = list(dict.fromkeys(user_ids))
    if unique_ids:
        found = set(
            db.scalars(
                select(User.id).where(
                    User.id.in_(unique_ids),
                    User.tenant_id == tenant_id,
                    User.is_active.is_(True),
                )
            )
        )
        missing = [str(u) for u in unique_ids if u not in found]
        if missing:
            raise UnknownUser(", ".join(missing))

    existing = set(
        db.scalars(
            select(DocumentAcknowledgment.user_id).where(
                DocumentAcknowledgment.version_id == version.id
            )
        )
    )
    created: list[DocumentAcknowledgment] = []
    for user_id in unique_ids:
        if user_id in existing:
            continue
        ack = DocumentAcknowledgment(
            tenant_id=tenant_id,
            document_id=document_id,
            version_id=version.id,
            user_id=user_id,
            assigned_by=assigned_by,
        )
        db.add(ack)
        created.append(ack)
    db.flush()
    return created


def acknowledge(
    db: Session, tenant_id: str, document_id: uuid.UUID, *, user_id: str
) -> DocumentAcknowledgment:
    """El usuario marca "leído y entendido" su acuse pendiente del documento."""
    ack = db.scalars(
        select(DocumentAcknowledgment).where(
            DocumentAcknowledgment.document_id == document_id,
            DocumentAcknowledgment.user_id == uuid.UUID(user_id),
            DocumentAcknowledgment.tenant_id == tenant_id,
        )
    ).first()
    if ack is None:
        raise AckNotFound(str(document_id))
    if ack.acknowledged_at is None:
        ack.acknowledged_at = datetime.now(UTC)
        db.flush()
    return ack


def list_acknowledgments(
    db: Session, tenant_id: str, document_id: uuid.UUID
) -> list[DocumentAcknowledgment]:
    return list(
        db.scalars(
            select(DocumentAcknowledgment)
            .where(
                DocumentAcknowledgment.document_id == document_id,
                DocumentAcknowledgment.tenant_id == tenant_id,
            )
            .order_by(DocumentAcknowledgment.assigned_at)
        )
    )


def my_pending(db: Session, tenant_id: str, user_id: str) -> list[DocumentAcknowledgment]:
    """Acuses del usuario aún sin marcar — los "obligatorios sin leer"."""
    return list(
        db.scalars(
            select(DocumentAcknowledgment)
            .where(
                DocumentAcknowledgment.tenant_id == tenant_id,
                DocumentAcknowledgment.user_id == uuid.UUID(user_id),
                DocumentAcknowledgment.acknowledged_at.is_(None),
            )
            .order_by(DocumentAcknowledgment.assigned_at)
        )
    )


# --------------------------------------------------------- retención/disposición
# La fecha de disposición calculada vive como propiedad ``disposition_date``
# en el modelo Document (se lee en cada respuesta). Aquí solo las acciones.


def set_legal_hold(
    db: Session, tenant_id: str, document_id: uuid.UUID, *, hold: bool
) -> Document:
    document = _get_document(db, tenant_id, document_id)
    if document.disposed_at is not None:
        raise InvalidTransition("Un documento ya dispuesto no admite cambios de retención legal")
    document.legal_hold = hold
    db.flush()
    db.refresh(document)
    return document


def dispose(
    db: Session,
    tenant_id: str,
    document_id: uuid.UUID,
    *,
    action: DispositionAction,
    notes: str,
    disposed_by: str,
) -> Document:
    """Disposición final: archivar o destruir un documento tras su retención.

    Bloqueada por ``legal_hold`` (litigio/requerimiento). Deja acta (motivo +
    quién + cuándo). No borra el registro — la disposición en sí es evidencia.
    """
    document = _get_document(db, tenant_id, document_id)
    if document.disposed_at is not None:
        raise InvalidTransition("El documento ya fue dispuesto")
    if document.legal_hold:
        raise InvalidTransition("El documento está bajo retención legal (legal hold): no se puede disponer")
    document.disposed_at = datetime.now(UTC)
    document.disposed_by = disposed_by
    document.disposition_action = action
    document.disposition_notes = notes
    db.flush()
    db.refresh(document)
    return document
