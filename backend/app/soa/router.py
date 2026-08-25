import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.soa import schemas, service
from app.soa.service import EntryNotFound, FrameworkNotFound, InvalidEntry
from app.tenants.models import Tenant

router = APIRouter(prefix="/api/v1/soa", tags=["soa (MOD·SOA)"])

can_write = require_tenant_roles("tenant_admin", "internal_auditor")


@router.post("/instantiate", response_model=schemas.InstantiateResult, status_code=status.HTTP_201_CREATED)
def instantiate(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(require_tenant_roles("tenant_admin")),
):
    tenant = db.get(Tenant, principal.tenant_id)
    try:
        created = service.instantiate(db, principal.tenant_id, framework_code=tenant.framework.code)
    except FrameworkNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Framework no encontrado") from exc
    return schemas.InstantiateResult(created=created)


@router.get("/entries", response_model=list[schemas.SoaEntryRead])
def list_entries(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_entries(db, principal.tenant_id)


@router.get("/summary", response_model=schemas.SoaSummary)
def get_summary(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.summary(db, principal.tenant_id)


@router.patch("/entries/{entry_id}", response_model=schemas.SoaEntryRead)
def update_entry(
    entry_id: uuid.UUID,
    payload: schemas.SoaEntryUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.update_entry(db, principal.tenant_id, entry_id, **payload.model_dump())
    except EntryNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entrada de SoA no encontrada") from exc
    except InvalidEntry as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
