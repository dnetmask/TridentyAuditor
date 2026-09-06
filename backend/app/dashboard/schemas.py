from pydantic import BaseModel

from app.compliance.schemas import ComplianceOverview


class DocumentStats(BaseModel):
    total_vigentes: int
    review_overdue: int
    review_upcoming: int
    pending_approval: int


class RiskStats(BaseModel):
    total: int
    open: int
    treating: int
    closed: int


class AuditStats(BaseModel):
    programs: int
    findings_total: int
    findings_open: int
    findings_closed: int


class LegalStats(BaseModel):
    total: int
    compliant: int
    partial: int
    non_compliant: int
    not_evaluated: int


class SoaStats(BaseModel):
    total: int
    applicable: int


class ProcessStats(BaseModel):
    total: int


class DashboardRead(BaseModel):
    compliance: ComplianceOverview
    documents: DocumentStats
    risks: RiskStats
    audits: AuditStats
    legal: LegalStats
    soa: SoaStats
    processes: ProcessStats
