import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.core.security import hash_password, verify_password
from app.tenants.models import Tenant


class AuthError(Exception):
    pass


class InvalidCredentials(AuthError):
    pass


class Forbidden(AuthError):
    pass


class InvalidUser(AuthError):
    pass


class EmailAlreadyExists(AuthError):
    pass


class UserNotFound(AuthError):
    pass


def authenticate(db: Session, email: str, password: str) -> User:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    user = db.scalars(stmt).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentials("Email o contraseña incorrectos")
    return user


def get_tenant_name(db: Session, tenant_id: uuid.UUID | None) -> str | None:
    if tenant_id is None:
        return None
    tenant = db.get(Tenant, tenant_id)
    return tenant.name if tenant else None


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
