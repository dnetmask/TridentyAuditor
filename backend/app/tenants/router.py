import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.activity.service import log_event
from app.core.database import get_db
from app.core.security import AuthPrincipal, require_super_admin
from app.frameworks.models import Framework
from app.tenants import schemas
from app.tenants.models import Tenant

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.post("", response_model=schemas.TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: schemas.TenantCreate,
    db: Session = Depends(get_db),
    principal: AuthPrincipal = Depends(require_super_admin),
) -> Tenant:
    framework = db.get(Framework, payload.framework_id)
    if framework is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Norma o estándar no encontrado")

    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El slug '{payload.slug}' ya existe") from exc
    db.refresh(tenant)
    log_event(
        db,
        action="tenants.created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=tenant.id,
        entity_type="tenant",
        entity_id=tenant.id,
        detail=f"{tenant.name} · norma {framework.code}",
    )
    return tenant


@router.get(
    "",
    response_model=list[schemas.TenantRead],
    dependencies=[Depends(require_super_admin)],
)
def list_tenants(db: Session = Depends(get_db)) -> list[Tenant]:
    return list(
        db.query(Tenant).options(selectinload(Tenant.framework)).order_by(Tenant.name).all()
    )


@router.get(
    "/{tenant_id}",
    response_model=schemas.TenantRead,
    dependencies=[Depends(require_super_admin)],
)
def get_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> Tenant:
    tenant = (
        db.query(Tenant)
        .options(selectinload(Tenant.framework))
        .filter(Tenant.id == tenant_id)
        .one_or_none()
    )
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant no encontrado")
    return tenant
