import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity.service import log_event_now
from app.auth.models import RefreshToken, User, UserRole
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import burn_password_check, hash_password, verify_password
from app.tenants.models import Tenant

settings = get_settings()


class AuthError(Exception):
    pass


class InvalidCredentials(AuthError):
    pass


class AccountLocked(AuthError):
    pass


class InvalidRefreshToken(AuthError):
    pass


class Forbidden(AuthError):
    pass


class InvalidUser(AuthError):
    pass


class EmailAlreadyExists(AuthError):
    pass


class UserNotFound(AuthError):
    pass


def bootstrap_super_admin(db: Session, *, email: str | None, password: str | None, full_name: str) -> None:
    """Crea la primera cuenta Super Admin desde variables de entorno, si se piden.

    Sin ninguna de las dos variables, no hace nada — el bootstrap manual
    (``scripts/create_super_admin.py``) sigue siendo la vía por defecto. Con
    solo una de las dos definida, falla fuerte: a medio configurar es peor
    que sin configurar, porque el arranque parecería exitoso sin haber
    creado ninguna cuenta utilizable.
    """
    if not email and not password:
        return
    if not email or not password:
        raise InvalidUser(
            "TRIDENTY_SUPER_ADMIN_EMAIL y TRIDENTY_SUPER_ADMIN_PASSWORD deben definirse juntas"
        )
    existing = db.scalars(select(User).where(func.lower(User.email) == email.lower())).first()
    if existing is not None:
        return
    db.add(
        User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.SUPER_ADMIN,
            tenant_id=None,
        )
    )
    db.commit()


def _register_failed_login(user_id: uuid.UUID, email: str, ip: str | None) -> None:
    """Suma un intento fallido y bloquea al llegar al umbral.

    En su propia transacción: la sesión del request hace rollback cuando el
    login termina en 401, así que el contador no puede viajar ahí.
    """
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return
        user.failed_login_attempts += 1
        locked = user.failed_login_attempts >= settings.login_lockout_attempts
        if locked:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
        db.commit()
    log_event_now(
        action="auth.login_locked" if locked else "auth.login_failed",
        actor_email=email,
        tenant_id=None,
        ip=ip,
        detail=f"Cuenta bloqueada {settings.login_lockout_minutes} min" if locked else None,
    )


def authenticate(db: Session, email: str, password: str, *, ip: str | None = None) -> User:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    user = db.scalars(stmt).first()

    if user is None:
        # Mismo costo de bcrypt que una cuenta real — sin esto, la latencia
        # del short-circuit revela qué emails están registrados.
        burn_password_check()
        log_event_now(action="auth.login_failed", actor_email=email, ip=ip)
        raise InvalidCredentials("Email o contraseña incorrectos")

    if user.locked_until is not None and user.locked_until > datetime.now(UTC):
        burn_password_check()
        raise AccountLocked(
            "Cuenta bloqueada temporalmente por intentos fallidos; intenta de nuevo más tarde"
        )

    if not user.is_active or not verify_password(password, user.password_hash):
        if user.is_active:
            _register_failed_login(user.id, email, ip)
        else:
            log_event_now(action="auth.login_failed", actor_email=email, ip=ip, detail="cuenta inactiva")
        raise InvalidCredentials("Email o contraseña incorrectos")

    if user.failed_login_attempts or user.locked_until is not None:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.flush()
    return user


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user_id: uuid.UUID) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash_refresh_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.flush()
    return raw


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[User, str]:
    """Valida el refresh token, lo revoca y emite uno nuevo (rotación por uso)."""
    stmt = select(RefreshToken).where(RefreshToken.token_hash == _hash_refresh_token(raw_token))
    stored = db.scalars(stmt).first()
    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise InvalidRefreshToken("Refresh token inválido, revocado o expirado")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshToken("La cuenta ya no está activa")
    stored.revoked_at = now
    new_raw = issue_refresh_token(db, user.id)
    return user, new_raw


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    """Revoca el refresh token si existe — idempotente, nunca falla."""
    stmt = select(RefreshToken).where(RefreshToken.token_hash == _hash_refresh_token(raw_token))
    stored = db.scalars(stmt).first()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.flush()


def get_tenant_name(db: Session, tenant_id: uuid.UUID | None) -> str | None:
    if tenant_id is None:
        return None
    tenant = db.get(Tenant, tenant_id)
    return tenant.name if tenant else None


def get_tenant_framework_code(db: Session, tenant_id: uuid.UUID | None) -> str | None:
    """El código de la norma del tenant (ej. ``ISO27001:2022`` o ``CNO-1960``),
    resuelto una vez en el login para que el frontend nunca tenga que
    adivinarlo o dejarlo escrito a mano — ver Fase 0 de la ruta de MOD·DOC.
    """
    if tenant_id is None:
        return None
    tenant = db.get(Tenant, tenant_id)
    return tenant.framework.code if tenant else None


def _assert_can_manage(creator_role: str, creator_tenant_id: str | None, target_role: UserRole, target_tenant_id: uuid.UUID | None) -> uuid.UUID | None:
    """Devuelve el tenant_id efectivo a usar, o levanta Forbidden/InvalidUser."""
    if creator_role == UserRole.SUPER_ADMIN.value:
        effective_tenant_id = target_tenant_id
    elif creator_role == UserRole.TENANT_ADMIN.value:
        if target_role == UserRole.SUPER_ADMIN:
            raise Forbidden("Un Admin del tenant no puede crear cuentas Super Admin")
        # El admin del tenant solo administra su propio tenant, sin importar
        # qué tenant_id haya llegado en el payload.
        effective_tenant_id = uuid.UUID(creator_tenant_id) if creator_tenant_id else None
    else:
        raise Forbidden("Rol sin permiso para administrar usuarios")

    if target_role == UserRole.SUPER_ADMIN and effective_tenant_id is not None:
        raise InvalidUser("Una cuenta Super Admin no debe tener tenant_id")
    if target_role != UserRole.SUPER_ADMIN and effective_tenant_id is None:
        raise InvalidUser("Este rol requiere un tenant_id")
    return effective_tenant_id


def create_user(
    db: Session,
    *,
    creator_role: str,
    creator_tenant_id: str | None,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    tenant_id: uuid.UUID | None,
) -> User:
    effective_tenant_id = _assert_can_manage(creator_role, creator_tenant_id, role, tenant_id)

    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        tenant_id=effective_tenant_id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        raise EmailAlreadyExists(f"El email '{email}' ya está registrado") from exc
    return user


def list_users(db: Session, *, viewer_role: str, viewer_tenant_id: str | None) -> list[User]:
    stmt = select(User).order_by(User.created_at)
    if viewer_role != UserRole.SUPER_ADMIN.value:
        stmt = stmt.where(User.tenant_id == viewer_tenant_id)
    return list(db.scalars(stmt))


def list_tenant_directory(db: Session, tenant_id: str) -> list[User]:
    """Nombres del propio tenant para selectores de dueño (SoA, riesgos) —

    a diferencia de ``list_users``, cualquier rol del tenant puede leerlo,
    no solo Admin del tenant / Super Admin.
    """
    stmt = (
        select(User)
        .where(User.tenant_id == tenant_id, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return list(db.scalars(stmt))


def _get_manageable_user(db: Session, user_id: uuid.UUID, *, viewer_role: str, viewer_tenant_id: str | None) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFound(str(user_id))
    if viewer_role != UserRole.SUPER_ADMIN.value and str(user.tenant_id) != str(viewer_tenant_id):
        # 404 en vez de 403: no confirmamos ni la existencia de usuarios de otro tenant.
        raise UserNotFound(str(user_id))
    return user


def update_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    editor_role: str,
    editor_tenant_id: str | None,
    full_name: str | None,
    role: UserRole | None,
    is_active: bool | None,
    password: str | None,
) -> User:
    user = _get_manageable_user(db, user_id, viewer_role=editor_role, viewer_tenant_id=editor_tenant_id)

    if role is not None and role != user.role:
        _assert_can_manage(editor_role, editor_tenant_id, role, user.tenant_id)
        if editor_role == UserRole.TENANT_ADMIN.value and user.role == UserRole.SUPER_ADMIN:
            raise Forbidden("Un Admin del tenant no puede editar cuentas Super Admin")
        user.role = role

    if full_name is not None:
        user.full_name = full_name
    if is_active is not None:
        user.is_active = is_active
    if password is not None:
        user.password_hash = hash_password(password)

    db.flush()
    return user
