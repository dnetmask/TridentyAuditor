import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activity.models import ActivityEvent
from app.core.database import SessionLocal


def client_ip(request: Request | None) -> str | None:
    """IP del cliente, respetando X-Forwarded-For si un proxy/ingress la puso."""
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def log_event(
    db: Session,
    *,
    action: str,
    actor_email: str | None = None,
    actor_user_id: str | uuid.UUID | None = None,
    tenant_id: str | uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | uuid.UUID | None = None,
    detail: str | None = None,
    ip: str | None = None,
) -> None:
    """Escribe un evento dentro de la transacción del request.

    Si el request falla y hace rollback, el evento se pierde junto con la
    acción que registraba — lo cual es correcto: solo se auditan acciones
    que sí ocurrieron. Para registrar *fracasos* (login fallido, cuenta
    bloqueada) usar ``log_event_now``, que persiste aunque el request
    termine en 4xx.
    """
    db.add(
        ActivityEvent(
            action=action,
            actor_email=actor_email,
            actor_user_id=uuid.UUID(str(actor_user_id)) if actor_user_id else None,
            tenant_id=uuid.UUID(str(tenant_id)) if tenant_id else None,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            detail=detail,
            ip_address=ip,
        )
    )


def log_event_now(**kwargs) -> None:
    """Como ``log_event`` pero en su propia transacción, confirmada de inmediato.

    Necesario para eventos que acompañan a un error HTTP: la sesión del
    request hace rollback al propagarse la excepción, así que ahí el evento
    no puede viajar en esa misma transacción.
    """
    with SessionLocal() as db:
        log_event(db, **kwargs)
        db.commit()


def list_tenant_events(db: Session, tenant_id: str, limit: int = 200) -> list[ActivityEvent]:
    stmt = (
        select(ActivityEvent)
        .where(ActivityEvent.tenant_id == tenant_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
