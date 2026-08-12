import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.risk import schemas, service
from app.risk.service import AssetNotFound, RiskNotFound

router = APIRouter(prefix="/api/v1/risk", tags=["risk (MOD·RSK)"])

can_write = require_tenant_roles("tenant_admin", "internal_auditor")


@router.post("/assets", response_model=schemas.AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: schemas.AssetCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    return service.create_asset(db, principal.tenant_id, **payload.model_dump())


@router.get("/assets", response_model=list[schemas.AssetRead])
def list_assets(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_assets(db, principal.tenant_id)


@router.patch("/assets/{asset_id}", response_model=schemas.AssetRead)
def update_asset(
    asset_id: uuid.UUID,
    payload: schemas.AssetUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.update_asset(db, principal.tenant_id, asset_id, **payload.model_dump())
    except AssetNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activo no encontrado") from exc


@router.post("/risks", response_model=schemas.RiskRead, status_code=status.HTTP_201_CREATED)
def create_risk(
    payload: schemas.RiskCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    return service.create_risk(db, principal.tenant_id, **payload.model_dump())


@router.get("/risks", response_model=list[schemas.RiskRead])
def list_risks(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_risks(db, principal.tenant_id)


@router.patch("/risks/{risk_id}", response_model=schemas.RiskRead)
def update_risk(
    risk_id: uuid.UUID,
    payload: schemas.RiskUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.update_risk(db, principal.tenant_id, risk_id, **payload.model_dump())
    except RiskNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Riesgo no encontrado") from exc
