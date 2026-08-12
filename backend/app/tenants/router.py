import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin_token
from app.tenants import schemas
from app.tenants.models import Tenant

router = APIRouter(
    prefix="/api/v1/tenants",
    tags=["tenants"],
    dependencies=[Depends(require_admin_token)],
)


@router.post("", response_model=schemas.TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: schemas.TenantCreate, db: Session = Depends(get_db)) -> Tenant:
    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El slug '{payload.slug}' ya existe") from exc
    db.refresh(tenant)
    return tenant


@router.get("", response_model=list[schemas.TenantRead])
def list_tenants(db: Session = Depends(get_db)) -> list[Tenant]:
    return list(db.query(Tenant).order_by(Tenant.name).all())


@router.get("/{tenant_id}", response_model=schemas.TenantRead)
def get_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant no encontrado")
    return tenant
