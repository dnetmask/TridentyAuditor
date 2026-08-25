import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.frameworks.models import Framework
from app.tenants.models import Tenant
from app.wizard import schemas, service
from app.wizard.service import InvalidTransition, PhaseNotFound, TaskNotFound

router = APIRouter(prefix="/api/v1/wizard", tags=["wizard (MOD·WZD)"])

# Arrancar la ruta (SGSI o CNO) es una decisión administrativa del tenant.
can_instantiate = require_tenant_roles("tenant_admin")
# Trabajar sobre las tareas: Admin del tenant o Auditor interno.
can_write = require_tenant_roles("tenant_admin", "internal_auditor")


def _tenant_framework_id(db: Session, tenant_id: str) -> uuid.UUID:
    tenant = db.get(Tenant, tenant_id)
    return tenant.framework_id


@router.get("/phases", response_model=list[schemas.PhaseWithTemplatesRead])
def list_phases(framework_code: str | None = None, db: Session = Depends(get_db)):
    framework_id = None
    if framework_code is not None:
        framework = db.query(Framework).filter_by(code=framework_code).one_or_none()
        if framework is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Norma o estándar no encontrado")
        framework_id = framework.id
    return service.list_phases(db, framework_id=framework_id)


@router.post("/instantiate", response_model=schemas.InstantiateResult, status_code=status.HTTP_201_CREATED)
def instantiate(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_instantiate),
):
    framework_id = _tenant_framework_id(db, principal.tenant_id)
    created = service.instantiate(db, principal.tenant_id, framework_id)
    return schemas.InstantiateResult(created=created)


@router.get("/progress", response_model=list[schemas.PhaseProgress])
def get_progress(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    framework_id = _tenant_framework_id(db, principal.tenant_id)
    return service.get_progress(db, principal.tenant_id, framework_id)


@router.post("/tasks", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.create_custom_task(db, principal.tenant_id, **payload.model_dump())
    except PhaseNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fase no encontrada") from exc


@router.patch("/tasks/{task_id}", response_model=schemas.TaskRead)
def update_task(
    task_id: uuid.UUID,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.update_task(db, principal.tenant_id, task_id, **payload.model_dump())
    except TaskNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/tasks/{task_id}/complete", response_model=schemas.TaskRead)
def complete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.complete_task(db, principal.tenant_id, task_id)
    except TaskNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/tasks/{task_id}/reopen", response_model=schemas.TaskRead)
def reopen_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        return service.reopen_task(db, principal.tenant_id, task_id)
    except TaskNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
