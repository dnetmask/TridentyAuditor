import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import schemas, service
from app.audit.service import FindingNotFound, InvalidFinding, InvalidProgram, ProgramNotFound
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles

router = APIRouter(prefix="/api/v1/audit", tags=["audit (MOD·AUD)"])

can_write = require_tenant_roles("tenant_admin", "internal_auditor")


@router.post("/programs", response_model=schemas.AuditProgramRead, status_code=status.HTTP_201_CREATED)
def create_program(
    payload: schemas.AuditProgramCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    return service.create_program(db, principal.tenant_id, **payload.model_dump())


@router.get("/programs", response_model=list[schemas.AuditProgramRead])
def list_programs(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_programs(db, principal.tenant_id)


@router.patch("/programs/{program_id}", response_model=schemas.AuditProgramRead)
def update_program(
    program_id: uuid.UUID,
    payload: schemas.AuditProgramUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.update_program(db, principal.tenant_id, program_id, **payload.model_dump())
    except ProgramNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auditoría no encontrada") from exc
    except InvalidProgram as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.post("/findings", response_model=schemas.AuditFindingRead, status_code=status.HTTP_201_CREATED)
def create_finding(
    payload: schemas.AuditFindingCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.create_finding(db, principal.tenant_id, **payload.model_dump())
    except ProgramNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auditoría no encontrada") from exc


@router.get("/findings", response_model=list[schemas.AuditFindingRead])
def list_findings(
    audit_id: uuid.UUID | None = None,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_findings(db, principal.tenant_id, audit_id=audit_id)


@router.patch("/findings/{finding_id}", response_model=schemas.AuditFindingRead)
def update_finding(
    finding_id: uuid.UUID,
    payload: schemas.AuditFindingUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.update_finding(db, principal.tenant_id, finding_id, **payload.model_dump())
    except FindingNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hallazgo no encontrado") from exc
    except InvalidFinding as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.get("/summary", response_model=schemas.AuditSummary)
def get_summary(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.summary(db, principal.tenant_id)
