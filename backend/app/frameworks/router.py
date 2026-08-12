import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.frameworks import schemas, service

router = APIRouter(prefix="/api/v1/frameworks", tags=["frameworks"])


@router.get("", response_model=list[schemas.FrameworkRead])
def list_frameworks(db: Session = Depends(get_db)) -> list[schemas.FrameworkRead]:
    return service.list_frameworks(db)


@router.get("/{code}", response_model=schemas.FrameworkDetailRead)
def get_framework(code: str, db: Session = Depends(get_db)) -> schemas.FrameworkDetailRead:
    framework = service.get_framework_by_code(db, code)
    if framework is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Framework '{code}' no encontrado")
    return framework


@router.get("/{code}/domains", response_model=list[schemas.DomainDetailRead])
def list_domains(code: str, db: Session = Depends(get_db)) -> list[schemas.DomainDetailRead]:
    domains = service.list_domains(db, code)
    if not domains and service.get_framework_by_code(db, code) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Framework '{code}' no encontrado")
    return domains


domains_router = APIRouter(prefix="/api/v1/domains", tags=["frameworks"])


@domains_router.get("/{domain_id}/controls", response_model=list[schemas.ControlDetailRead])
def list_controls(domain_id: uuid.UUID, db: Session = Depends(get_db)) -> list[schemas.ControlDetailRead]:
    return service.list_controls(db, domain_id)


controls_router = APIRouter(prefix="/api/v1/controls", tags=["frameworks"])


@controls_router.get("/{control_id}", response_model=schemas.ControlDetailRead)
def get_control(control_id: uuid.UUID, db: Session = Depends(get_db)) -> schemas.ControlDetailRead:
    control = service.get_control(db, control_id)
    if control is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Control no encontrado")
    return control
