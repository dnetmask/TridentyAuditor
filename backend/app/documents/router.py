import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity.service import client_ip, log_event
from app.core.config import get_settings
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.documents import lifecycle, schemas, service
from app.documents.filetypes import DisallowedFileType, validate_and_resolve_type
from app.documents.lifecycle import AckNotFound, NoApprovedVersion, UnknownUser
from app.documents.models import DocumentOrigin
from app.documents.service import (
    ApprovalNotAllowed,
    DocumentNotFound,
    FileIntegrityError,
    FileMissing,
    InvalidTransition,
    UnknownControl,
    VersionNotFound,
)
from app.documents.stamping import stamp_pdf

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


# También antes de /{document_id}: "my-acknowledgments" no es un UUID.
@router.get("/my-acknowledgments", response_model=list[schemas.AcknowledgmentRead])
def my_acknowledgments(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """Los acuses pendientes del usuario actual — sus 'obligatorios sin leer'."""
    return lifecycle.my_pending(db, principal.tenant_id, principal.user_id)


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


@router.post("/{document_id}/publish", response_model=schemas.AcknowledgmentSummary)
def publish_document(
    document_id: uuid.UUID,
    payload: schemas.PublishRequest,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    """Pide acuse de recibo de la versión vigente a un conjunto de usuarios."""
    try:
        created = lifecycle.publish_for_acknowledgment(
            db,
            principal.tenant_id,
            document_id,
            user_ids=payload.user_ids,
            assigned_by=principal.email,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except NoApprovedVersion as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Solo se puede distribuir un documento con una versión aprobada",
        ) from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except UnknownUser as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Usuarios inválidos: {exc}"
        ) from exc
    log_event(
        db,
        action="documents.published",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"{len(created)} destinatario(s)",
    )
    return _ack_summary(db, principal.tenant_id, document_id)


@router.get("/{document_id}/acknowledgments", response_model=schemas.AcknowledgmentSummary)
def document_acknowledgments(
    document_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return _ack_summary(db, principal.tenant_id, document_id)


@router.post("/{document_id}/acknowledge", response_model=schemas.AcknowledgmentRead)
def acknowledge_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """El usuario marca 'leído y entendido' su acuse del documento."""
    try:
        ack = lifecycle.acknowledge(db, principal.tenant_id, document_id, user_id=principal.user_id)
    except AckNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No tienes un acuse pendiente para este documento"
        ) from exc
    log_event(
        db,
        action="documents.acknowledged",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail="leído y entendido",
    )
    return ack


def _ack_summary(db: Session, tenant_id: str, document_id: uuid.UUID) -> schemas.AcknowledgmentSummary:
    entries = lifecycle.list_acknowledgments(db, tenant_id, document_id)
    acknowledged = sum(1 for e in entries if e.acknowledged_at is not None)
    return schemas.AcknowledgmentSummary(
        total=len(entries),
        acknowledged=acknowledged,
        pending=len(entries) - acknowledged,
        entries=entries,
    )


# --- Retención / disposición final (Fase 5) ---
@router.post("/{document_id}/legal-hold", response_model=schemas.DocumentDetailRead)
def set_legal_hold(
    document_id: uuid.UUID,
    payload: schemas.LegalHoldRequest,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_review),
):
    """Activa/levanta la retención legal — mientras está activa, no se dispone."""
    try:
        lifecycle.set_legal_hold(db, principal.tenant_id, document_id, hold=payload.hold)
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.legal_hold",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail="activado" if payload.hold else "levantado",
    )
    return service.get_document(db, principal.tenant_id, document_id)


@router.post("/{document_id}/dispose", response_model=schemas.DocumentDetailRead)
def dispose_document(
    document_id: uuid.UUID,
    payload: schemas.DispositionRequest,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_review),
):
    """Disposición final (archivar/destruir) tras cumplir la retención."""
    try:
        lifecycle.dispose(
            db,
            principal.tenant_id,
            document_id,
            action=payload.action,
            notes=payload.notes,
            disposed_by=principal.email,
        )
    except DocumentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.disposed",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"{payload.action.value} · {payload.notes}",
    )
    return service.get_document(db, principal.tenant_id, document_id)


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


# Marca de agua según el estado de lo servido: cualquier cosa que no sea la
# copia vigente sale marcada (ISO 7.5.3.d — prevenir uso de info obsoleta).
_WATERMARKS = {
    "draft": "BORRADOR",
    "in_review": "EN REVISIÓN",
    "obsolete": "OBSOLETO",
}


@router.get("/{document_id}/versions/{version_number}/file")
def download_version_file(
    document_id: uuid.UUID,
    version_number: int,
    request: Request,
    inline: bool = False,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """Sirve el binario de la versión. ``?inline=true`` lo entrega para leer
    en el navegador (botón Ver) en vez de forzar la descarga.

    Los PDF salen estampados: pie de "copia no controlada" en toda página y
    marca de agua diagonal si la versión no es la vigente o el documento
    está derogado. La verificación SHA-256 corre sobre el original ANTES de
    estampar — el sello nunca enmascara un binario adulterado.
    """
    try:
        version, path = service.get_version_file(db, principal.tenant_id, document_id, version_number)
        document = service.get_document(db, principal.tenant_id, document_id)
    except (DocumentNotFound, VersionNotFound) as exc:
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
        detail=f"versión {version_number}" + (" · vista inline" if inline else ""),
        ip=client_ip(request),
    )

    media_type = version.content_type or "application/octet-stream"
    filename = version.original_filename or f"{document_id}-v{version_number}"
    disposition = "inline" if inline else "attachment"

    if media_type == "application/pdf":
        if document.retired_at is not None:
            watermark = "DEROGADO"
        else:
            watermark = _WATERMARKS.get(version.status.value)
        footer = (
            f"Copia no controlada · {document.code} v{version.version_number} · "
            f"descargada el {date.today().isoformat()} por {principal.email}"
        )
        content = stamp_pdf(path.read_bytes(), footer_text=footer, watermark=watermark)
        safe_name = filename.replace('"', "")
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"'},
        )

    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type=disposition,
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
    # Cualquier miembro del tenant puede LLAMAR — el gerente de un área puede
    # tener rol auditor o visualizador. Quién puede firmar QUÉ paso lo decide
    # el servicio (gerente del área o Admin; seguridad = solo Admin).
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """Firma el siguiente paso pendiente de la aprobación multinivel.

    Documento con área: firma 1 = gerente del área (o Admin en su lugar),
    firma 2 = seguridad de la información (Admin). Sin área: una sola firma
    de seguridad. La versión pasa a ``approved`` con la última firma.
    """
    try:
        version, step = service.sign_approval(
            db,
            principal.tenant_id,
            document_id,
            version_number,
            signer_email=principal.email,
            signer_user_id=principal.user_id,
            signer_role=principal.role,
        )
    except VersionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada") from exc
    except ApprovalNotAllowed as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="documents.signed",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="document",
        entity_id=document_id,
        detail=f"versión {version_number} · firma {step.value} · sello {version.file_sha256 or 'sin hash'}",
    )
    if version.status.value == "approved":
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
