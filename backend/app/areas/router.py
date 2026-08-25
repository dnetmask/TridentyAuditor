import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity.service import log_event
from app.areas import schemas
from app.areas.models import Area
from app.auth.models import User
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles

router = APIRouter(prefix="/api/v1/areas", tags=["areas"])

# Definir el mapa de áreas del tenant es gobierno — solo el Admin del tenant.
# Leerlas puede cualquiera: alimentan selectores y filtros.
can_manage = require_tenant_roles("tenant_admin")


def _validate_manager(db: Session, tenant_id: str, manager_user_id: uuid.UUID | None) -> None:
    """El gerente debe ser una cuenta activa DEL MISMO tenant.

    ``users`` vive en el plano de control sin RLS — este es exactamente el
    tipo de chequeo manual que no puede faltar (ver análisis S2).
    """
    if manager_user_id is None:
        return
    manager = db.scalars(
        select(User).where(
            User.id == manager_user_id,
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
        )
    ).first()
    if manager is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El gerente debe ser un usuario activo de este tenant",
        )


@router.post("", response_model=schemas.AreaRead, status_code=status.HTTP_201_CREATED)
def create_area(
    payload: schemas.AreaCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_manage),
):
    _validate_manager(db, principal.tenant_id, payload.manager_user_id)
    area = Area(
        tenant_id=principal.tenant_id,
        name=payload.name,
        manager_user_id=payload.manager_user_id,
    )
    db.add(area)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El área '{payload.name}' ya existe") from exc
    log_event(
        db,
        action="areas.created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="area",
        entity_id=area.id,
        detail=payload.name,
    )
    return area


@router.get("", response_model=list[schemas.AreaRead])
def list_areas(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return list(db.scalars(select(Area).order_by(Area.name)))


@router.patch("/{area_id}", response_model=schemas.AreaRead)
def update_area(
    area_id: uuid.UUID,
    payload: schemas.AreaUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_manage),
):
    area = db.get(Area, area_id)
    if area is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Área no encontrada")
    changes = payload.model_dump(exclude_unset=True)
    if "manager_user_id" in changes:
        _validate_manager(db, principal.tenant_id, changes["manager_user_id"])
        area.manager_user_id = changes["manager_user_id"]
    if changes.get("name"):
        area.name = changes["name"]
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El área '{payload.name}' ya existe") from exc
    return area
