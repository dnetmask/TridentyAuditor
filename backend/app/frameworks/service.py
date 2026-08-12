import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.frameworks.models import Control, Domain, Framework


def list_frameworks(db: Session) -> list[Framework]:
    return list(db.scalars(select(Framework).order_by(Framework.code)))


def get_framework_by_code(db: Session, code: str) -> Framework | None:
    stmt = (
        select(Framework)
        .where(Framework.code == code)
        .options(selectinload(Framework.domains).selectinload(Domain.controls))
    )
    return db.scalars(stmt).first()


def list_domains(db: Session, framework_code: str) -> list[Domain]:
    stmt = (
        select(Domain)
        .join(Framework)
        .where(Framework.code == framework_code)
        .options(selectinload(Domain.controls))
        .order_by(Domain.order_index)
    )
    return list(db.scalars(stmt))


def list_controls(db: Session, domain_id: uuid.UUID) -> list[Control]:
    stmt = (
        select(Control)
        .where(Control.domain_id == domain_id)
        .options(selectinload(Control.requirements))
        .order_by(Control.order_index)
    )
    return list(db.scalars(stmt))


def get_control(db: Session, control_id: uuid.UUID) -> Control | None:
    stmt = (
        select(Control)
        .where(Control.id == control_id)
        .options(selectinload(Control.requirements))
    )
    return db.scalars(stmt).first()
