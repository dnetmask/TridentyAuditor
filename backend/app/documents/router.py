import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity.service import client_ip, log_event
from app.core.config import get_settings
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.documents import schemas, service
from app.documents.filetypes import DisallowedFileType, validate_and_resolve_type
from app.documents.models import DocumentOrigin
from app.documents.service import (
    DocumentNotFound,
    FileIntegrityError,
    FileMissing,
    InvalidTransition,
    UnknownControl,
    VersionNotFound,
)

settings = get_settings()

router = APIRouter(prefix="/api/v1/documents", tags=["documents (MOD·DOC)"])

# Cargar/editar documentos: Admin del tenant o Auditor interno (necesita
# poder subir su propia evidencia de auditoría). Aprobar/rechazar/derogar es
# un acto de autoridad — se restringe a Admin del tenant (sección 07).
can_write = require_tenant_roles("tenant_admin", "internal_auditor")
can_review = require_tenant_roles("tenant_admin")

_MAX_FILE_BYTES = settings.documents_max_file_size_mb * 1024 * 1024
_CHUNK_BYTES = 1024 * 1024


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    """Lee el archivo por chunks (corta apenas se pasa del límite, en vez de
    cargar un cuerpo arbitrario a memoria primero) y valida tipo + firma
    binaria contra la allowlist. Devuelve (contenido, media type real)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > _MAX_FILE_BYTES:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                f"El archivo supera el máximo permitido de {settings.documents_max_file_size_mb} MB",
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo está vacío")
    try:
        media_type = validate_and_resolve_type(file.filename or "", content[:16])
    except DisallowedFileType as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, exc.message) from exc
    return content, media_type


# Antes de las rutas /{document_id}: "next-code" no es un UUID.
@router.get("/next-code", response_model=schemas.NextCodeRead)
def next_code(
    document_type: str,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """Consecutivo sugerido por tipo (POL-001, PRC-014, …) — editable al crear."""
    return schemas.NextCodeRead(code=service.suggest_next_code(db, principal.tenant_id, document_type))


@router.post("", response_model=schemas.DocumentDetailRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    code: str = Form(..., min_length=1, max_length=50),
    title: str = Form(..., min_length=1, max_length=255),
    document_type: str = Form(..., min_length=1, max_length=50),
    retention_months: int | None = Form(None, ge=1),
    change_summary: str | None = Form(None),
    area_id: uuid.UUID | None = Form(None),
    implementation_date: date | None = Form(None),
    review_frequency_months: int | None = Form(None, ge=1),
    next_review_date: date | None = Form(None),
    origin: DocumentOrigin = Form(DocumentOrigin.INTERNAL),
    external_source: str | None = Form(None, max_length=255),
    control_ids: list[uuid.UUID] = Form(default=[]),
    file: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    content, media_type = await _read_upload(file)
    try:
        document = service.create_document(
            db,
            principal.tenant_id,
            code=code,
            title=title,
            document_type=document_type,
            retention_months=retention_months,
            created_by=principal.email,
            change_summary=change_summary,
            file_content=content,
            original_filename=file.filename or code,
            content_type=media_type,
            area_id=area_id,
            implementation_date=implementation_date,
            review_frequency_months=review_frequency_months,
            next_review_date=next_review_date,
            origin=origin,
            external_source=external_source,
            control_ids=control_ids,
        )
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El código '{code}' ya existe") from exc
    except UnknownControl as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Controles inexistentes: {exc}"
        ) from exc
    log_event(
        db,
        action="documents.created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document.id,
        detail=f"{code} · {title}",
    )
    return document


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


@router.patch("/{document_id}", response_model=schemas.DocumentDetailRead)
def update_document(
    document_id: uuid.UUID,
    payload: schemas.DocumentUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    changes = payload.model_dump(exclude_unset=True)
    try:
        document = service.update_document(db, principal.tenant_id, document_id, **changes)
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except UnknownControl as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Controles inexistentes: {exc}"
        ) from exc
    log_event(
        db,
        action="documents.updated",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"campos: {', '.join(sorted(changes)) or 'ninguno'}",
    )
    return document


@router.post("/{document_id}/retire", response_model=schemas.DocumentDetailRead)
def retire_document(
    document_id: uuid.UUID,
    payload: schemas.DocumentRetireRequest,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_review),
):
    """Derogación formal del documento completo, con motivo obligatorio."""
    try:
        document = service.retire_document(
            db, principal.tenant_id, document_id, reason=payload.reason, retired_by=principal.email
        )
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.retired",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=payload.reason,
    )
    return document


@router.post(
    "/{document_id}/versions",
    response_model=schemas.DocumentVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_version(
    document_id: uuid.UUID,
    # Obligatorio desde la Fase 1: control de cambios (ISO 7.5.3.e) — una
    # versión nueva sin decir qué cambió no es control documental.
    change_summary: str = Form(..., min_length=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    content, media_type = await _read_upload(file)
    try:
        version = service.create_new_version(
            db,
            principal.tenant_id,
            document_id,
            created_by=principal.email,
            change_summary=change_summary,
            file_content=content,
            original_filename=file.filename or "documento",
            content_type=media_type,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.version_created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"versión {version.version_number}",
    )
    return version


@router.get("/{document_id}/versions/{version_number}/file")
def download_version_file(
    document_id: uuid.UUID,
    version_number: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    try:
        version, path = service.get_version_file(db, principal.tenant_id, document_id, version_number)
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except FileMissing as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Esta versión no tiene un archivo almacenado (registro anterior a la subida de archivos)",
        ) from exc
    except FileIntegrityError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "El archivo en el almacenamiento no coincide con el hash registrado al subirlo — "
            "integridad comprometida; no se sirve",
        ) from exc
    log_event(
        db,
        action="documents.downloaded",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"versión {version_number}",
        ip=client_ip(request),
    )
    return FileResponse(
        path,
        media_type=version.content_type or "application/octet-stream",
        filename=version.original_filename or f"{document_id}-v{version_number}",
    )


@router.post("/{document_id}/versions/{version_number}/submit", response_model=schemas.DocumentVersionRead)
def submit_for_review(
    document_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    try:
        version = service.submit_for_review(db, principal.tenant_id, document_id, version_number)
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.submitted",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"versión {version_number}",
    )
    return version


@router.post("/{document_id}/versions/{version_number}/reject", response_model=schemas.DocumentVersionRead)
def reject_version(
    document_id: uuid.UUID,
    version_number: int,
    payload: schemas.VersionRejectRequest,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_review),
):
    try:
        version = service.reject_version(
            db,
            principal.tenant_id,
            document_id,
            version_number,
            reason=payload.reason,
            rejected_by=principal.email,
        )
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.rejected",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"versión {version_number} · {payload.reason}",
    )
    return version


@router.post("/{document_id}/versions/{version_number}/approve", response_model=schemas.DocumentVersionRead)
def approve_version(
    document_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_review),
):
    try:
        version = service.approve_version(
            db, principal.tenant_id, document_id, version_number, principal.email
        )
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.approved",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"versión {version_number}",
    )
    return version
