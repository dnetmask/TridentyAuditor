"""Dashboard de entrada (Fase 4) — un agregado del estado del tenant.

Reúne, en una sola llamada, lo que hoy vive repartido entre módulos: el
indicador de cumplimiento y conteos rápidos por módulo, para que el usuario
que entra vea de un vistazo dónde está parado y qué le falta. No introduce
lógica de negocio nueva — orquesta consultas de solo lectura.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditFinding, AuditProgram, FindingStatus
from app.compliance.service import get_overview
from app.documents.models import Document, DocumentStatus, DocumentVersion
from app.legal.models import LegalComplianceRating, LegalRequirement, LegalRequirementStatus
from app.processes.models import Process
from app.risk.models import Risk, RiskStatus
from app.soa.models import SoaEntry

_SOON_DAYS = 30


def _document_stats(db: Session, tenant_id: str) -> dict:
    vigentes = list(
        db.scalars(
            select(Document).where(
                Document.tenant_id == tenant_id, Document.retired_at.is_(None)
            )
        )
    )
    today = date.today()
    soon = today + timedelta(days=_SOON_DAYS)
    overdue = sum(1 for d in vigentes if d.next_review_date and d.next_review_date < today)
    upcoming = sum(
        1 for d in vigentes if d.next_review_date and today <= d.next_review_date <= soon
    )
    pending = db.scalar(
        select(func.count(DocumentVersion.id)).where(
            DocumentVersion.tenant_id == tenant_id,
            DocumentVersion.status == DocumentStatus.IN_REVIEW,
        )
    )
    return {
        "total_vigentes": len(vigentes),
        "review_overdue": overdue,
        "review_upcoming": upcoming,
        "pending_approval": pending or 0,
    }


def _risk_stats(db: Session, tenant_id: str) -> dict:
    rows = db.execute(
        select(Risk.status, func.count(Risk.id))
        .where(Risk.tenant_id == tenant_id)
        .group_by(Risk.status)
    ).all()
    by_status = {status.value: count for status, count in rows}
    return {
        "total": sum(by_status.values()),
        "open": by_status.get(RiskStatus.OPEN.value, 0),
        "treating": by_status.get(RiskStatus.TREATING.value, 0),
        "closed": by_status.get(RiskStatus.CLOSED.value, 0),
    }


def _audit_stats(db: Session, tenant_id: str) -> dict:
    programs = db.scalar(
        select(func.count(AuditProgram.id)).where(AuditProgram.tenant_id == tenant_id)
    )
    rows = db.execute(
        select(AuditFinding.status, func.count(AuditFinding.id))
        .where(AuditFinding.tenant_id == tenant_id)
        .group_by(AuditFinding.status)
    ).all()
    by_status = {status.value: count for status, count in rows}
    open_findings = by_status.get(FindingStatus.OPEN.value, 0) + by_status.get(
        FindingStatus.IN_PROGRESS.value, 0
    )
    return {
        "programs": programs or 0,
        "findings_total": sum(by_status.values()),
        "findings_open": open_findings,
        "findings_closed": by_status.get(FindingStatus.CLOSED.value, 0),
    }


def _legal_stats(db: Session, tenant_id: str) -> dict:
    rows = db.execute(
        select(LegalRequirement.compliance_rating, func.count(LegalRequirement.id))
        .where(
            LegalRequirement.tenant_id == tenant_id,
            LegalRequirement.status == LegalRequirementStatus.IN_FORCE,
        )
        .group_by(LegalRequirement.compliance_rating)
    ).all()
    by_rating = {rating.value: count for rating, count in rows}
    return {
        "total": sum(by_rating.values()),
        "compliant": by_rating.get(LegalComplianceRating.COMPLIANT.value, 0),
        "partial": by_rating.get(LegalComplianceRating.PARTIAL.value, 0),
        "non_compliant": by_rating.get(LegalComplianceRating.NON_COMPLIANT.value, 0),
        "not_evaluated": by_rating.get(LegalComplianceRating.NOT_EVALUATED.value, 0),
    }


def _soa_stats(db: Session, tenant_id: str) -> dict:
    total = db.scalar(select(func.count(SoaEntry.id)).where(SoaEntry.tenant_id == tenant_id))
    applicable = db.scalar(
        select(func.count(SoaEntry.id)).where(
            SoaEntry.tenant_id == tenant_id, SoaEntry.is_applicable.is_(True)
        )
    )
    return {"total": total or 0, "applicable": applicable or 0}


def _process_stats(db: Session, tenant_id: str) -> dict:
    total = db.scalar(select(func.count(Process.id)).where(Process.tenant_id == tenant_id))
    return {"total": total or 0}


def get_dashboard(db: Session, tenant_id: str) -> dict:
    return {
        "compliance": get_overview(db, tenant_id),
        "documents": _document_stats(db, tenant_id),
        "risks": _risk_stats(db, tenant_id),
        "audits": _audit_stats(db, tenant_id),
        "legal": _legal_stats(db, tenant_id),
        "soa": _soa_stats(db, tenant_id),
        "processes": _process_stats(db, tenant_id),
    }
