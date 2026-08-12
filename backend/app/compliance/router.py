from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.compliance import schemas, service
from app.core.security import TenantPrincipal, decode_tenant_token, get_tenant_db

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


@router.get("/overview", response_model=schemas.ComplianceOverview)
def get_overview(
    db: Session = Depends(get_tenant_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.get_overview(db, principal.tenant_id)
