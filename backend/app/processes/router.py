import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity.service import log_event
from app.auth.models import User
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.processes import schemas, service
from app.processes.service import InvalidParent, ProcessNotFound, UnknownDocument

router = APIRouter(prefix="/api/v1/processes", tags=["processes (MOD·PRC)"])

# El mapa de procesos es gobierno del SGSI: lo define el Admin del tenant.
can_manage = require_tenant_roles("tenant_admin")


def _validate_owner(db: Session, tenant_id: str, user_id: uuid.UUID | None) -> None:
    if user_id is None:
        return
    owner = db.scalars(
        select(User).where(
            User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True)
        )
    ).first()
    if owner is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El responsable debe ser un usuario activo de este tenant",
        )


@router.get("/tree", response_model=list[schemas.ProcessNode])
def process_tree(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """Árbol de procesos con documentos por nodo y conteo acumulado."""
    return service.build_tree(db, principal.tenant_id)


@router.get("", response_model=list[schemas.ProcessRead])
def list_processes(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_processes(db, principal.tenant_id)


@router.post("", response_model=schemas.ProcessRead, status_code=status.HTTP_201_CREATED)
def create_process(
    payload: schemas.ProcessCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_manage),
):
    _validate_owner(db, principal.tenant_id, payload.owner_user_id)
    try:
        process = service.create_process(
            db,
            principal.tenant_id,
            name=payload.name,
            description=payload.description,
            parent_id=payload.parent_id,
            owner_user_id=payload.owner_user_id,
            order_index=payload.order_index,
            document_ids=payload.document_ids,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"El proceso '{payload.name}' ya existe"
        ) from exc
    except InvalidParent as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except UnknownDocument as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Documentos inexistentes: {exc}"
        ) from exc
    log_event(
        db,
        action="processes.created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="process",
        entity_id=process.id,
        detail=payload.name,
    )
    return process


@router.patch("/{process_id}", response_model=schemas.ProcessRead)
def update_process(
    process_id: uuid.UUID,
    payload: schemas.ProcessUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_manage),
):
    changes = payload.model_dump(exclude_unset=True)
    if "owner_user_id" in changes:
        _validate_owner(db, principal.tenant_id, changes["owner_user_id"])
    try:
        process = service.update_process(db, principal.tenant_id, process_id, **changes)
    except ProcessNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proceso no encontrado") from exc
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"El proceso '{payload.name}' ya existe"
        ) from exc
    except InvalidParent as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except UnknownDocument as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Documentos inexistentes: {exc}"
        ) from exc
    log_event(
        db,
        action="processes.updated",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="process",
        entity_id=process_id,
        detail=f"campos: {', '.join(sorted(changes)) or 'ninguno'}",
    )
    return process


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process(
    process_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_manage),
):
    try:
        service.delete_process(db, principal.tenant_id, process_id)
    except ProcessNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proceso no encontrado") from exc
    log_event(
        db,
        action="processes.deleted",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="process",
        entity_id=process_id,
        detail="",
    )
