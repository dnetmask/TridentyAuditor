import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from app.frameworks.models import Control, Domain, Framework
from app.soa.models import ImplementationStatus, SoaEntry


class SoaError(Exception):
    pass


class FrameworkNotFound(SoaError):
    pass


class EntryNotFound(SoaError):
    pass


class InvalidEntry(SoaError):
    pass


DEFAULT_FRAMEWORK_CODE = "ISO27001:2022"


def instantiate(db: Session, tenant_id: str, framework_code: str = DEFAULT_FRAMEWORK_CODE) -> int:
    """Crea una SoaEntry (aplicable, sin implementar) por cada control del framework."""
    framework = db.scalars(select(Framework).where(Framework.code == framework_code)).first()
    if framework is None:
        raise FrameworkNotFound(framework_code)

    control_ids = list(
        db.scalars(
            select(Control.id).join(Domain).where(Domain.framework_id == framework.id)
        )
    )
    existing = set(
        db.scalars(
            select(SoaEntry.control_id).where(
                SoaEntry.tenant_id == tenant_id, SoaEntry.control_id.in_(control_ids)
            )
        )
    )

    created = 0
    for control_id in control_ids:
        if control_id in existing:
            continue
        db.add(SoaEntry(tenant_id=tenant_id, control_id=control_id))
        created += 1
    db.flush()
    return created


def list_entries(db: Session, tenant_id: str) -> list[SoaEntry]:
    stmt = (
        select(SoaEntry)
        .where(SoaEntry.tenant_id == tenant_id)
        .join(SoaEntry.control)
        .join(Control.domain)
        .options(contains_eager(SoaEntry.control).contains_eager(Control.domain))
        .order_by(Domain.order_index, Control.order_index)
    )
    return list(db.scalars(stmt))


def _get_entry(db: Session, tenant_id: str, entry_id: uuid.UUID) -> SoaEntry:
    stmt = select(SoaEntry).where(SoaEntry.id == entry_id, SoaEntry.tenant_id == tenant_id)
    entry = db.scalars(stmt).first()
    if entry is None:
        raise EntryNotFound(str(entry_id))
    return entry


def update_entry(
    db: Session,
    tenant_id: str,
    entry_id: uuid.UUID,
    *,
    is_applicable: bool | None,
    justification: str | None,
    implementation_status: ImplementationStatus | None,
    owner_user_id: uuid.UUID | None,
    evidence_document_id: uuid.UUID | None,
    notes: str | None,
) -> SoaEntry:
    entry = _get_entry(db, tenant_id, entry_id)

    if is_applicable is not None:
        entry.is_applicable = is_applicable
    if justification is not None:
        entry.justification = justification
    if implementation_status is not None:
        entry.implementation_status = implementation_status
    if owner_user_id is not None:
        entry.owner_user_id = owner_user_id
    if evidence_document_id is not None:
        entry.evidence_document_id = evidence_document_id
    if notes is not None:
        entry.notes = notes

    if not entry.is_applicable and not (entry.justification and entry.justification.strip()):
        raise InvalidEntry("Un control excluido requiere justificación")

    db.flush()
    return entry


def summary(db: Session, tenant_id: str) -> dict:
    entries = list_entries(db, tenant_id)
    return {
        "total": len(entries),
        "applicable": sum(1 for e in entries if e.is_applicable),
        "excluded": sum(1 for e in entries if not e.is_applicable),
        "implemented": sum(1 for e in entries if e.implementation_status == ImplementationStatus.IMPLEMENTED),
        "in_progress": sum(1 for e in entries if e.implementation_status == ImplementationStatus.IN_PROGRESS),
        "not_started": sum(1 for e in entries if e.implementation_status == ImplementationStatus.NOT_STARTED),
    }
