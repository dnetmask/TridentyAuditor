import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import (
    AuditFinding,
    AuditProgram,
    AuditStatus,
    FindingClassification,
    FindingStatus,
)
from app.documents.service import has_approved_version


class AuditError(Exception):
    pass


class ProgramNotFound(AuditError):
    pass


class FindingNotFound(AuditError):
    pass


class InvalidFinding(AuditError):
    pass


class InvalidProgram(AuditError):
    pass


def create_program(
    db: Session,
    tenant_id: str,
    *,
    title: str,
    scope: str | None,
    domain_id: uuid.UUID | None,
    auditor_user_id: uuid.UUID | None,
    planned_date,
) -> AuditProgram:
    program = AuditProgram(
        tenant_id=tenant_id,
        title=title,
        scope=scope,
        domain_id=domain_id,
        auditor_user_id=auditor_user_id,
        planned_date=planned_date,
    )
    db.add(program)
    db.flush()
    return program


def list_programs(db: Session, tenant_id: str) -> list[AuditProgram]:
    stmt = select(AuditProgram).where(AuditProgram.tenant_id == tenant_id).order_by(AuditProgram.created_at)
    return list(db.scalars(stmt))


def _get_program(db: Session, tenant_id: str, program_id: uuid.UUID) -> AuditProgram:
    stmt = select(AuditProgram).where(AuditProgram.id == program_id, AuditProgram.tenant_id == tenant_id)
    program = db.scalars(stmt).first()
    if program is None:
        raise ProgramNotFound(str(program_id))
    return program


def update_program(
    db: Session,
    tenant_id: str,
    program_id: uuid.UUID,
    *,
    title: str | None,
    scope: str | None,
    domain_id: uuid.UUID | None,
    auditor_user_id: uuid.UUID | None,
    planned_date,
    executed_date,
    status,
    auditor_score: int | None = None,
    auditor_evaluation: str | None = None,
) -> AuditProgram:
    program = _get_program(db, tenant_id, program_id)
    if title is not None:
        program.title = title
    if scope is not None:
        program.scope = scope
    if domain_id is not None:
        program.domain_id = domain_id
    if auditor_user_id is not None:
        program.auditor_user_id = auditor_user_id
    if planned_date is not None:
        program.planned_date = planned_date
    if executed_date is not None:
        program.executed_date = executed_date
    if status is not None:
        program.status = status

    # La evaluación del auditor se diligencia al cerrar la auditoría: el estado
    # resultante (el que llega en este update, o el ya guardado) debe ser
    # "completed". Así el puntaje refleja una auditoría ejecutada, no una plan.
    if auditor_score is not None or auditor_evaluation is not None:
        if program.status != AuditStatus.COMPLETED:
            raise InvalidProgram(
                "La evaluación del auditor solo se registra al cerrar la auditoría "
                "(estado 'completed')"
            )
        if auditor_score is not None:
            program.auditor_score = auditor_score
        if auditor_evaluation is not None:
            program.auditor_evaluation = auditor_evaluation

    db.flush()
    return program


def create_finding(
    db: Session,
    tenant_id: str,
    *,
    audit_id: uuid.UUID,
    control_id: uuid.UUID | None,
    classification: FindingClassification,
    description: str,
    root_cause: str | None,
    corrective_action: str | None,
    owner_user_id: uuid.UUID | None,
    due_date,
    progress_pct: int = 0,
    estimated_cost: float | None = None,
) -> AuditFinding:
    _get_program(db, tenant_id, audit_id)  # valida que la auditoría exista y sea del tenant
    finding = AuditFinding(
        tenant_id=tenant_id,
        audit_id=audit_id,
        control_id=control_id,
        classification=classification,
        description=description,
        root_cause=root_cause,
        corrective_action=corrective_action,
        owner_user_id=owner_user_id,
        due_date=due_date,
        progress_pct=progress_pct,
        estimated_cost=estimated_cost,
    )
    db.add(finding)
    db.flush()
    return finding


def list_findings(db: Session, tenant_id: str, audit_id: uuid.UUID | None = None) -> list[AuditFinding]:
    stmt = select(AuditFinding).where(AuditFinding.tenant_id == tenant_id)
    if audit_id is not None:
        stmt = stmt.where(AuditFinding.audit_id == audit_id)
    stmt = stmt.order_by(AuditFinding.created_at)
    return list(db.scalars(stmt))


def _get_finding(db: Session, tenant_id: str, finding_id: uuid.UUID) -> AuditFinding:
    stmt = select(AuditFinding).where(AuditFinding.id == finding_id, AuditFinding.tenant_id == tenant_id)
    finding = db.scalars(stmt).first()
    if finding is None:
        raise FindingNotFound(str(finding_id))
    return finding


def update_finding(
    db: Session,
    tenant_id: str,
    finding_id: uuid.UUID,
    *,
    control_id: uuid.UUID | None,
    classification: FindingClassification | None,
    description: str | None,
    root_cause: str | None,
    corrective_action: str | None,
    owner_user_id: uuid.UUID | None,
    due_date,
    status: FindingStatus | None,
    evidence_document_id: uuid.UUID | None,
    progress_pct: int | None = None,
    estimated_cost: float | None = None,
) -> AuditFinding:
    finding = _get_finding(db, tenant_id, finding_id)

    if control_id is not None:
        finding.control_id = control_id
    if classification is not None:
        finding.classification = classification
    if description is not None:
        finding.description = description
    if root_cause is not None:
        finding.root_cause = root_cause
    if corrective_action is not None:
        finding.corrective_action = corrective_action
    if owner_user_id is not None:
        finding.owner_user_id = owner_user_id
    if due_date is not None:
        finding.due_date = due_date
    if evidence_document_id is not None:
        finding.evidence_document_id = evidence_document_id
    if progress_pct is not None:
        finding.progress_pct = progress_pct
    if estimated_cost is not None:
        finding.estimated_cost = estimated_cost
    if status is not None:
        finding.status = status

    if finding.status == FindingStatus.CLOSED:
        if finding.evidence_document_id is None or not has_approved_version(
            db, tenant_id, finding.evidence_document_id
        ):
            raise InvalidFinding(
                "Un hallazgo cerrado exige evidencia: vincule un documento de MOD·DOC con una versión aprobada"
            )
        if finding.closed_at is None:
            finding.closed_at = datetime.now(UTC)
        # Una acción CAPA cerrada está, por definición, al 100% de avance.
        finding.progress_pct = 100
    else:
        finding.closed_at = None

    db.flush()
    return finding


def summary(db: Session, tenant_id: str) -> dict:
    programs = list_programs(db, tenant_id)
    findings = list_findings(db, tenant_id)
    open_capa = [f for f in findings if f.status != FindingStatus.CLOSED]
    avg_progress = (
        round(sum(f.progress_pct for f in open_capa) / len(open_capa)) if open_capa else 0
    )
    open_cost = float(sum(f.estimated_cost or 0 for f in open_capa))
    return {
        "total_programs": len(programs),
        "total_findings": len(findings),
        "open_findings": sum(1 for f in findings if f.status == FindingStatus.OPEN),
        "in_progress_findings": sum(1 for f in findings if f.status == FindingStatus.IN_PROGRESS),
        "closed_findings": sum(1 for f in findings if f.status == FindingStatus.CLOSED),
        "major_nc": sum(1 for f in findings if f.classification == FindingClassification.MAJOR_NC),
        "minor_nc": sum(1 for f in findings if f.classification == FindingClassification.MINOR_NC),
        "capa_open_avg_progress": avg_progress,
        "capa_open_estimated_cost": open_cost,
    }
