import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.activity.service import client_ip, log_event
from app.auth import schemas, service
from app.auth.service import (
    AccountLocked,
    EmailAlreadyExists,
    Forbidden,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidUser,
    UserNotFound,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import (
    AuthPrincipal,
    TenantPrincipal,
    decode_principal,
    decode_tenant_token,
    issue_access_token,
    require_admin_principal,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()

login_limiter = SlidingWindowLimiter(limit=settings.login_rate_limit_per_minute)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if not login_limiter.allow(ip or "unknown"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos de inicio de sesión; espera un minuto",
        )
    try:
        user = service.authenticate(db, payload.email, payload.password, ip=ip)
    except AccountLocked as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    except InvalidCredentials as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    access_token, expires_in = issue_access_token(user.id)
    refresh_token = service.issue_refresh_token(db, user.id)
    log_event(
        db,
        action="auth.login",
        actor_email=user.email,
        actor_user_id=user.id,
        tenant_id=user.tenant_id,
        ip=ip,
    )
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=service.get_tenant_name(db, user.tenant_id),
        framework_code=service.get_tenant_framework_code(db, user.tenant_id),
    )


@router.post("/refresh", response_model=schemas.RefreshResponse)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """Cambia un refresh token vigente por un access token nuevo.

    Rotación en cada uso: el refresh token entregado queda revocado y se
    devuelve uno nuevo — un token filtrado sirve a lo sumo una vez.
    """
    try:
        user, new_refresh = service.rotate_refresh_token(db, payload.refresh_token)
    except InvalidRefreshToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    access_token, expires_in = issue_access_token(user.id)
    return schemas.RefreshResponse(
        access_token=access_token, refresh_token=new_refresh, expires_in=expires_in
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.LogoutRequest, request: Request, db: Session = Depends(get_db)):
    """Revoca el refresh token — el access token corto expira solo.

    Idempotente a propósito: cerrar sesión con un token ya revocado o
    inexistente no es un error que valga la pena reportarle a nadie.
    """
    service.revoke_refresh_token(db, payload.refresh_token)
    log_event(db, action="auth.logout", ip=client_ip(request))
    return None


@router.get("/me", response_model=schemas.MeRead)
def me(principal: AuthPrincipal = Depends(decode_principal)):
    return schemas.MeRead(
        user_id=principal.user_id,
        email=principal.email,
        full_name=principal.full_name,
        role=principal.role,
        tenant_id=principal.tenant_id,
    )


@router.get("/directory", response_model=list[schemas.DirectoryUserRead])
def directory(
    db: Session = Depends(get_db),
    principal: TenantPrincipal = Depends(decode_tenant_token),
):
    return service.list_tenant_directory(db, principal.tenant_id)


@router.post("/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    principal: AuthPrincipal = Depends(require_admin_principal),
):
    try:
        user = service.create_user(
            db,
            creator_role=principal.role,
            creator_tenant_id=principal.tenant_id,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
            tenant_id=payload.tenant_id,
        )
    except Forbidden as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except InvalidUser as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except EmailAlreadyExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    log_event(
        db,
        action="users.created",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=user.tenant_id,
        entity_type="user",
        entity_id=user.id,
        detail=f"{user.email} · rol {user.role.value}",
    )
    return user


@router.get("/users", response_model=list[schemas.UserRead])
def list_users(
    db: Session = Depends(get_db),
    principal: AuthPrincipal = Depends(require_admin_principal),
):
    return service.list_users(db, viewer_role=principal.role, viewer_tenant_id=principal.tenant_id)


@router.patch("/users/{user_id}", response_model=schemas.UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    principal: AuthPrincipal = Depends(require_admin_principal),
):
    try:
        user = service.update_user(
            db,
            user_id,
            editor_role=principal.role,
            editor_tenant_id=principal.tenant_id,
            **payload.model_dump(),
        )
    except UserNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado") from exc
    except Forbidden as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except InvalidUser as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    changed = [k for k, v in payload.model_dump().items() if v is not None and k != "password"]
    if payload.password is not None:
        changed.append("password")
    log_event(
        db,
        action="users.updated",
        actor_email=principal.email,
        actor_user_id=principal.user_id,
        tenant_id=user.tenant_id,
        entity_type="user",
        entity_id=user.id,
        detail=f"{user.email} · campos: {', '.join(changed) or 'ninguno'}",
    )
    return user
