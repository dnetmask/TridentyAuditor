import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import schemas, service
from app.auth.service import EmailAlreadyExists, Forbidden, InvalidCredentials, InvalidUser, UserNotFound
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import AuthPrincipal, TenantPrincipal, decode_principal, decode_tenant_token, require_admin_principal

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


def _issue_token(user) -> str:
    claims = {
        "sub": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
    }
    if user.tenant_id is not None:
        claims["tenant_id"] = str(user.tenant_id)
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    try:
        user = service.authenticate(db, payload.email, payload.password)
    except InvalidCredentials as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    return schemas.TokenResponse(
        access_token=_issue_token(user),
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=service.get_tenant_name(db, user.tenant_id),
    )


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
        return service.update_user(
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
