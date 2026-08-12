"""Dev-only helper to mint tenant JWTs, mirroring scripts/make_dev_token.py.

Only mounted when ``TRIDENTY_ENVIRONMENT=local`` (see app/main.py) — this is
a stand-in for the Keycloak/OIDC login flow of Fase 2 (sección 05 del
documento de arquitectura), never something to expose alongside a real
identity provider.
"""

import uuid

import jwt
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/dev", tags=["dev (solo local)"])


class DevTokenRequest(BaseModel):
    tenant_id: uuid.UUID
    sub: str = Field(default="dev-user", min_length=1, max_length=255)
    role: str = Field(default="tenant_admin", min_length=1, max_length=50)


class DevTokenResponse(BaseModel):
    access_token: str


@router.post("/token", response_model=DevTokenResponse)
def mint_dev_token(payload: DevTokenRequest) -> DevTokenResponse:
    settings = get_settings()
    token = jwt.encode(
        {"tenant_id": str(payload.tenant_id), "sub": payload.sub, "role": payload.role},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return DevTokenResponse(access_token=token)
