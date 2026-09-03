import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity.service import log_event
from app.auth.models import User
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db, require_tenant_roles
from app.documents.models import Document
from app.legal import schemas, service
from app.legal.models import LegalRequirement

router = APIRouter(prefix="/api/v1/legal-requirements", tags=["legal (MOD·LEG)"])

# Mantener la matriz: Admin del tenant o Auditor interno (es quien la
# levanta y la evalúa). Leerla puede cualquier rol del tenant.
can_write = require_tenant_roles("tenant_admin", "internal_auditor")


def _validate_responsible(db: Session, tenant_id: str, user_id: uuid.UUID | None) -> None:
    """Mismo chequeo manual que el gerente de área: ``users`` no tiene RLS."""
    if user_id is None:
        return
    responsible = db.scalars(
        select(User).where(
            User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True)
        )
    ).first()
    if responsible is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El responsable debe ser un usuario activo de este tenant",
        )


def _validate_evidence(db: Session, tenant_id: str, document_id: uuid.UUID | None) -> None:
    if document_id is None:
        return
    # RLS ya restringe al tenant; el filtro explícito documenta la intención.
    document = db.scalars(
        select(Document.id).where(Document.id == document_id, Document.tenant_id == tenant_id)
    ).first()
    if document is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El documento de evidencia no existe en este tenant",
        )


# Antes de /{requirement_id}: "summary" no es un UUID.
@router.get("/summary", response_model=schemas.LegalSummaryRead)
def get_summary(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.compliance_summary(db, principal.tenant_id)


@router.post("", response_model=schemas.LegalRequirementRead, status_code=status.HTTP_201_CREATED)
def create_requirement(
    payload: schemas.LegalRequirementCreate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    _validate_responsible(db, principal.tenant_id, payload.responsible_user_id)
    _validate_evidence(db, principal.tenant_id, payload.evidence_document_id)
    requirement = LegalRequirement(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(requirement)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"El requisito '{payload.name}' ya existe"
        ) from exc
    log_event(
        db,
        action="legal.created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="legal_requirement",
        entity_id=requirement.id,
        detail=payload.name,
    )
    return requirement


@router.get("", response_model=list[schemas.LegalRequirementRead])
def list_requirements(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return list(db.scalars(select(LegalRequirement).order_by(LegalRequirement.name)))


@router.patch("/{requirement_id}", response_model=schemas.LegalRequirementRead)
def update_requirement(
    requirement_id: uuid.UUID,
    payload: schemas.LegalRequirementUpdate,
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(can_write),
):
    requirement = db.get(LegalRequirement, requirement_id)
    if requirement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requisito no encontrado")
    changes = payload.model_dump(exclude_unset=True)
    if "responsible_user_id" in changes:
        _validate_responsible(db, principal.tenant_id, changes["responsible_user_id"])
    if "evidence_document_id" in changes:
        _validate_evidence(db, principal.tenant_id, changes["evidence_document_id"])
    for field, value in changes.items():
        setattr(requirement, field, value)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"El requisito '{payload.name}' ya existe"
        ) from exc
    log_event(
        db,
        action="legal.updated",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        entity_type="legal_requirement",
        entity_id=requirement_id,
        detail=f"campos: {', '.join(sorted(changes)) or 'ninguno'}",
    )
    return requirement
