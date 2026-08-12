import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db
from app.documents import schemas, service
from app.documents.service import DocumentNotFound, InvalidTransition, VersionNotFound

router = APIRouter(prefix="/api/v1/documents", tags=["documents (MOD·DOC)"])


@router.post("", response_model=schemas.DocumentDetailRead, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: schemas.DocumentCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.create_document(db, principal.tenant_id, **payload.model_dump())
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El código '{payload.code}' ya existe") from exc


@router.get("", response_model=list[schemas.DocumentDetailRead])
def list_documents(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_documents(db, principal.tenant_id)


@router.get("/{document_id}", response_model=schemas.DocumentDetailRead)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.get_document(db, principal.tenant_id, document_id)
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc


@router.post(
    "/{document_id}/versions",
    response_model=schemas.DocumentVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_new_version(
    document_id: uuid.UUID,
    payload: schemas.NewVersionCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.create_new_version(db, principal.tenant_id, document_id, **payload.model_dump())
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{document_id}/versions/{version_number}/submit", response_model=schemas.DocumentVersionRead)
def submit_for_review(
    document_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.submit_for_review(db, principal.tenant_id, document_id, version_number)
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{document_id}/versions/{version_number}/reject", response_model=schemas.DocumentVersionRead)
def reject_version(
    document_id: uuid.UUID,
    version_number: int,
    payload: schemas.ReviewDecision,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.reject_version(db, principal.tenant_id, document_id, version_number)
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{document_id}/versions/{version_number}/approve", response_model=schemas.DocumentVersionRead)
def approve_version(
    document_id: uuid.UUID,
    version_number: int,
    payload: schemas.ReviewDecision,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        return service.approve_version(db, principal.tenant_id, document_id, version_number, payload.actor)
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
