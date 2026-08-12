from collections.abc import Generator
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_tenant_db_session

settings = get_settings()


@dataclass
class TenantPrincipal:
    tenant_id: str
    user_id: str
    role: str


def decode_tenant_token(authorization: str | None = Header(default=None)) -> TenantPrincipal:
    """Resolves the tenant/user/role from the bearer JWT.

    Stand-in for the Tenant Resolver Middleware described in la sección 04-05
    del documento de arquitectura. HS256 with a shared secret is a placeholder
    for local development and tests; Fase 2 reemplaza esto con validación de
    tokens OIDC emitidos por Keycloak (firma asimétrica, federación por
    tenant).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el header Authorization: Bearer <token>",
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
        ) from exc

    tenant_id = payload.get("tenant_id")
    user_id = payload.get("sub")
    role = payload.get("role", "collaborator")
    if not tenant_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no incluye tenant_id/sub",
        )
    return TenantPrincipal(tenant_id=tenant_id, user_id=user_id, role=role)


def get_tenant_db(
    principal: TenantPrincipal = Depends(decode_tenant_token),
) -> Generator[Session, None, None]:
    yield from get_tenant_db_session(principal.tenant_id)


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Temporary guard for cross-tenant/provisioning endpoints.

    Placeholder for the Super Admin Netmask role until Keycloak-backed
    role checks land (sección 07 del documento de arquitectura).
    """
    if x_admin_token != settings.admin_bootstrap_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere X-Admin-Token de Super Admin Netmask",
        )
