import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.documents.models import Document, DocumentStatus, DocumentVersion
from app.wizard.models import TenantWizardTask, WizardPhase, WizardTaskStatus, WizardTaskTemplate


class WizardError(Exception):
    pass


class TaskNotFound(WizardError):
    pass


class PhaseNotFound(WizardError):
    pass


class InvalidTransition(WizardError):
    pass


def list_phases(db: Session) -> list[WizardPhase]:
    stmt = select(WizardPhase).options(selectinload(WizardPhase.templates)).order_by(WizardPhase.number)
    return list(db.scalars(stmt))


def instantiate(db: Session, tenant_id: str) -> int:
    """Crea, para este tenant, una TenantWizardTask por cada plantilla que aún no tenga.

    Idempotente: llamarlo de nuevo (p.ej. después de agregar plantillas
    nuevas al checklist global) solo agrega lo que falte.
    """
    templates = list(
        db.scalars(
            select(WizardTaskTemplate)
            .join(WizardPhase)
            .order_by(WizardPhase.number, WizardTaskTemplate.order_index)
        )
    )
    existing_template_ids = {
        row[0]
        for row in db.execute(
            select(TenantWizardTask.template_id).where(
                TenantWizardTask.tenant_id == tenant_id,
                TenantWizardTask.template_id.is_not(None),
            )
        )
    }

    created = 0
    for template in templates:
        if template.id in existing_template_ids:
            continue
        db.add(
            TenantWizardTask(
                tenant_id=tenant_id,
                phase_id=template.phase_id,
                template_id=template.id,
                title=template.title,
                description=template.description,
                requires_evidence=template.requires_evidence,
                order_index=template.order_index,
            )
        )
        created += 1
    db.flush()
    return created


def _tasks_by_phase(db: Session, tenant_id: str) -> dict[uuid.UUID, list[TenantWizardTask]]:
    tasks = list(
        db.scalars(
            select(TenantWizardTask)
            .where(TenantWizardTask.tenant_id == tenant_id)
            .order_by(TenantWizardTask.order_index, TenantWizardTask.created_at)
        )
    )
    by_phase: dict[uuid.UUID, list[TenantWizardTask]] = {}
    for task in tasks:
        by_phase.setdefault(task.phase_id, []).append(task)
    return by_phase


def get_progress(db: Session, tenant_id: str) -> list[dict]:
    phases = list(db.scalars(select(WizardPhase).order_by(WizardPhase.number)))
    by_phase = _tasks_by_phase(db, tenant_id)

    progress = []
    previous_complete = True
    for phase in phases:
        tasks = by_phase.get(phase.id, [])
        done_count = sum(1 for t in tasks if t.status == WizardTaskStatus.DONE)
        complete = bool(tasks) and done_count == len(tasks)

        if complete:
            status = "complete"
        elif previous_complete:
            status = "current"
        else:
            status = "locked"

        progress.append(
            {
                "phase": phase,
                "status": status,
                "tasks": tasks,
                "done_count": done_count,
                "total_count": len(tasks),
            }
        )
        previous_complete = complete

    return progress


def _is_phase_unlocked(db: Session, tenant_id: str, phase_id: uuid.UUID) -> bool:
    for entry in get_progress(db, tenant_id):
        if entry["phase"].id == phase_id:
            return entry["status"] in ("current", "complete")
    raise PhaseNotFound(str(phase_id))


def create_custom_task(
    db: Session,
    tenant_id: str,
    *,
    phase_id: uuid.UUID,
    title: str,
    description: str | None,
    requires_evidence: bool,
    owner: str | None,
    due_date,
) -> TenantWizardTask:
    if db.get(WizardPhase, phase_id) is None:
        raise PhaseNotFound(str(phase_id))
    max_order = db.scalar(
        select(func.max(TenantWizardTask.order_index)).where(
            TenantWizardTask.tenant_id == tenant_id, TenantWizardTask.phase_id == phase_id
        )
    )
    task = TenantWizardTask(
        tenant_id=tenant_id,
        phase_id=phase_id,
        template_id=None,
        title=title,
        description=description,
        requires_evidence=requires_evidence,
        owner=owner,
        due_date=due_date,
        order_index=(max_order or 0) + 1,
    )
    db.add(task)
    db.flush()
    return task


def _get_task(db: Session, tenant_id: str, task_id: uuid.UUID) -> TenantWizardTask:
    stmt = select(TenantWizardTask).where(
        TenantWizardTask.id == task_id, TenantWizardTask.tenant_id == tenant_id
    )
    task = db.scalars(stmt).first()
    if task is None:
        raise TaskNotFound(str(task_id))
    return task


def update_task(
    db: Session,
    tenant_id: str,
    task_id: uuid.UUID,
    *,
    owner: str | None,
    due_date,
    evidence_document_id: uuid.UUID | None,
) -> TenantWizardTask:
    task = _get_task(db, tenant_id, task_id)
    if task.status == WizardTaskStatus.DONE:
        raise InvalidTransition("La tarea ya está completada; reábrala antes de editarla")
    if owner is not None:
        task.owner = owner
    if due_date is not None:
        task.due_date = due_date
    if evidence_document_id is not None:
        task.evidence_document_id = evidence_document_id
    db.flush()
    return task


def _has_approved_version(db: Session, tenant_id: str, document_id: uuid.UUID) -> bool:
    stmt = (
        select(DocumentVersion)
        .join(Document)
        .where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            DocumentVersion.tenant_id == tenant_id,
            DocumentVersion.status == DocumentStatus.APPROVED,
        )
    )
    return db.scalars(stmt).first() is not None


def complete_task(db: Session, tenant_id: str, task_id: uuid.UUID) -> TenantWizardTask:
    task = _get_task(db, tenant_id, task_id)
    if task.status == WizardTaskStatus.DONE:
        raise InvalidTransition("La tarea ya está completada")

    if not _is_phase_unlocked(db, tenant_id, task.phase_id):
        raise InvalidTransition("La fase anterior todavía no está completa")

    if task.requires_evidence:
        if task.evidence_document_id is None or not _has_approved_version(
            db, tenant_id, task.evidence_document_id
        ):
            raise InvalidTransition(
                "Esta tarea exige evidencia: vincule un documento de MOD·DOC con una versión aprobada"
            )

    task.status = WizardTaskStatus.DONE
    task.completed_at = datetime.now(UTC)
    db.flush()
    return task


def reopen_task(db: Session, tenant_id: str, task_id: uuid.UUID) -> TenantWizardTask:
    task = _get_task(db, tenant_id, task_id)
    if task.status != WizardTaskStatus.DONE:
        raise InvalidTransition("La tarea no está completada")
    task.status = WizardTaskStatus.PENDING
    task.completed_at = None
    db.flush()
    return task
