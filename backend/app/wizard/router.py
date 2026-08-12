import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db
from app.wizard import schemas, service
from app.wizard.service import InvalidTransition, PhaseNotFound, TaskNotFound

router = APIRouter(prefix="/api/v1/wizard", tags=["wizard (MOD·WZD)"])


@router.get("/phases", response_model=list[schemas.PhaseWithTemplatesRead])
def list_phases(db: Session = Depends(get_db)):
    return service.list_phases(db)


@router.post("/instantiate", response_model=schemas.InstantiateResult, status_code=status.HTTP_201_CREATED)
def instantiate(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    created = service.instantiate(db, principal.tenant_id)
    return schemas.InstantiateResult(created=created)


@router.get("/progress", response_model=list[schemas.PhaseProgress])
def get_progress(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.get_progress(db, principal.tenant_id)


@router.post("/tasks", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
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
    principal: TenantPrincipal = Depends(decode_tenant_token),
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
    principal: TenantPrincipal = Depends(decode_tenant_token),
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
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.reopen_task(db, principal.tenant_id, task_id)
    except TaskNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
