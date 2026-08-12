from collections.abc import Generator
from dataclasses import dataclass

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_tenant_db_session

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


@dataclass
class AuthPrincipal:
    """Identidad decodificada del JWT, sin asumir que hay un tenant.

    Un Super Admin tiene ``tenant_id is None`` — es cross-tenant por diseño
    (sección 07 del documento de arquitectura).
    """

    user_id: str
    email: str
    full_name: str
    role: str
    tenant_id: str | None


@dataclass
class TenantPrincipal:
    """Identidad ya confirmada como perteneciente a un tenant."""

    tenant_id: str
    user_id: str
    email: str
    role: str


def _decode_jwt(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el header Authorization: Bearer <token>",
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
        ) from exc


def decode_principal(authorization: str | None = Header(default=None)) -> AuthPrincipal:
    """Resuelve cualquier cuenta autenticada — Super Admin o de un tenant.

    Placeholder de la Fase 1 para lo que en la Fase 2 valida tokens OIDC
    emitidos por Keycloak (sección 05 del documento de arquitectura).
    """
    payload = _decode_jwt(authorization)
    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")
    if not user_id or not email or not role:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token incompleto")
    return AuthPrincipal(
        user_id=user_id,
        email=email,
        full_name=payload.get("full_name", email),
        role=role,
        tenant_id=payload.get("tenant_id"),
    )


def decode_tenant_token(authorization: str | None = Header(default=None)) -> TenantPrincipal:
    """Como ``decode_principal``, pero exige que el token dé acceso a un tenant.

    Un token de Super Admin no trae ``tenant_id`` — por diseño no puede abrir
    una sesión de base de datos con RLS de ningún tenant (sección 07:
    "sin acceso a documentos de cliente salvo soporte autorizado y
    auditado"). Esta función es la que hace cumplir eso.
    """
    payload = _decode_jwt(authorization)
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("sub")
    role = payload.get("role")
    if not tenant_id or not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no da acceso a un tenant (¿es una cuenta Super Admin?)",
        )
    return TenantPrincipal(tenant_id=tenant_id, user_id=user_id, email=payload.get("email", ""), role=role)


def get_tenant_db(
    principal: TenantPrincipal = Depends(decode_tenant_token),
) -> Generator[Session, None, None]:
    yield from get_tenant_db_session(principal.tenant_id)


def require_super_admin(principal: AuthPrincipal = Depends(decode_principal)) -> AuthPrincipal:
    if principal.role != "super_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requiere rol Super Admin")
    return principal


def require_admin_principal(principal: AuthPrincipal = Depends(decode_principal)) -> AuthPrincipal:
    """Super Admin (cualquier tenant) o Admin del tenant (el propio) — sección 07."""
    if principal.role not in ("super_admin", "tenant_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requiere rol Super Admin o Admin del tenant")
    return principal


def require_tenant_roles(*roles: str):
    """Dependencia factory: exige que el token del tenant tenga uno de estos roles."""

    def _dependency(principal: TenantPrincipal = Depends(decode_tenant_token)) -> TenantPrincipal:
        if principal.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Requiere uno de estos roles: {', '.join(roles)}"
            )
        return principal

    return _dependency
