from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db
from app.dashboard import schemas, service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=schemas.DashboardRead)
def dashboard_overview(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    """Estado agregado del tenant para la pantalla de entrada — cualquier rol."""
    return service.get_dashboard(db, principal.tenant_id)
