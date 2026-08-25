from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.activity import schemas, service
from app.core.database import get_db
from app.core.security import TenantPrincipal, require_tenant_roles

router = APIRouter(prefix="/api/v1/activity", tags=["activity (bitácora)"])

# La bitácora es material de gobierno: solo el Admin del tenant la consulta.
can_read = require_tenant_roles("tenant_admin")


@router.get("", response_model=list[schemas.ActivityEventRead])
def list_events(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    principal: TenantPrincipal = Depends(can_read),
):
    """Últimos eventos del propio tenant, más reciente primero.

    Usa ``get_db`` (no la sesión RLS) porque ``activity_events`` guarda
    también eventos sin tenant; el filtro por el tenant del token se aplica
    aquí, igual que en el listado de usuarios.
    """
    return service.list_tenant_events(db, principal.tenant_id, limit=limit)
