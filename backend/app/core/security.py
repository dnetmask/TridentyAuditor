import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_tenant_db_session

settings = get_settings()

# Hash real de una contraseña aleatoria descartada — se compara contra él
# cuando el email no existe, para que el login tarde lo mismo exista o no la
# cuenta (sin esto, el short-circuit revela por timing qué emails están
# registrados).
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"tridenty-timing-equalizer", bcrypt.gensalt()).decode("utf-8")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def burn_password_check() -> None:
    """Consume el mismo costo de bcrypt que una verificación real."""
    bcrypt.checkpw(b"not-the-password", _DUMMY_PASSWORD_HASH.encode("utf-8"))


def issue_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Emite el access token y devuelve (token, segundos de vida).

    Solo lleva identidad (``sub``) y vigencia: rol, tenant y estado de la
    cuenta se re-leen de la base de datos en cada request (ver
    ``_load_active_user``), así que degradar o desactivar a alguien surte
    efecto de inmediato — no cuando el token expire.
    """
    now = datetime.now(UTC)
    expires_in = settings.access_token_minutes * 60
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires_in


@dataclass
class AuthPrincipal:
    """Identidad verificada contra la base de datos, sin asumir que hay un tenant.

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
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            # exp obligatorio: un token sin vigencia (como los emitidos antes
            # de la Fase S1) se rechaza en vez de valer para siempre.
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
        ) from exc


def _resolve_principal(authorization: str | None) -> AuthPrincipal:
    """Decodifica el JWT y re-verifica la cuenta contra la base de datos.

    El token solo se usa para probar identidad (``sub`` firmado); rol, tenant,
    email y estado activo salen de la BD en cada request. Es la pieza que hace
    revocable la sesión: desactivar la cuenta invalida todos sus tokens al
    instante, y un cambio de rol no requiere re-login para aplicarse.
    """
    payload = _decode_jwt(authorization)
    try:
        user_uuid = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token incompleto") from exc

    from app.auth.models import User  # import tardío: evita ciclo con auth.service

    with SessionLocal() as db:
        user = db.get(User, user_uuid)
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión revocada o cuenta inactiva")
        return AuthPrincipal(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            tenant_id=str(user.tenant_id) if user.tenant_id is not None else None,
        )


def decode_principal(authorization: str | None = Header(default=None)) -> AuthPrincipal:
    """Resuelve cualquier cuenta autenticada — Super Admin o de un tenant.

    Placeholder de la Fase 1 para lo que en la Fase 2 valida tokens OIDC
    emitidos por Keycloak (sección 05 del documento de arquitectura).
    """
    return _resolve_principal(authorization)


def decode_tenant_token(authorization: str | None = Header(default=None)) -> TenantPrincipal:
    """Como ``decode_principal``, pero exige que el token dé acceso a un tenant.

    Un token de Super Admin no trae ``tenant_id`` — por diseño no puede abrir
    una sesión de base de datos con RLS de ningún tenant (sección 07:
    "sin acceso a documentos de cliente salvo soporte autorizado y
    auditado"). Esta función es la que hace cumplir eso.
    """
    principal = _resolve_principal(authorization)
    if principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no da acceso a un tenant (¿es una cuenta Super Admin?)",
        )
    return TenantPrincipal(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        email=principal.email,
        role=principal.role,
    )


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
