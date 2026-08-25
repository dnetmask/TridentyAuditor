"""Pruebas de la Fase S1: vigencia y revocación de sesiones, lockout,
refresh tokens, allowlist de archivos, cabeceras de seguridad y bitácora."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings, get_settings
from app.core.ratelimit import SlidingWindowLimiter

settings = get_settings()


def _mint(sub: str, *, expired: bool = False, secret: str | None = None, omit_exp: bool = False) -> str:
    now = datetime.now(UTC)
    claims: dict = {"sub": sub, "iat": now}
    if not omit_exp:
        claims["exp"] = now - timedelta(minutes=5) if expired else now + timedelta(minutes=15)
    return jwt.encode(claims, secret or settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _create_tenant_user(client, super_admin_headers, make_tenant, email, password="correcthorse123"):
    tenant = make_tenant()
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": email,
            "password": password,
            "full_name": "Usuario S1",
            "role": "tenant_admin",
            "tenant_id": tenant["id"],
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return tenant, resp.json()


# ---------------------------------------------------------------- tokens

def test_expired_token_is_rejected(client, make_tenant, token_factory):
    tenant = make_tenant()
    valid = token_factory(tenant["id"])
    payload = jwt.decode(valid, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    expired = _mint(payload["sub"], expired=True)
    resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_token_without_exp_is_rejected(client, make_tenant, token_factory):
    """Los tokens eternos de antes de la Fase S1 dejan de valer."""
    tenant = make_tenant()
    valid = token_factory(tenant["id"])
    payload = jwt.decode(valid, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    eternal = _mint(payload["sub"], omit_exp=True)
    resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {eternal}"})
    assert resp.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(client):
    forged = _mint(str(uuid.uuid4()), secret="attacker-controlled-secret-123456")
    resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_malformed_token_is_rejected(client):
    resp = client.get("/api/v1/documents", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert resp.status_code == 401


def test_token_of_nonexistent_user_is_rejected(client):
    """Un sub firmado pero sin usuario detrás ya no autentica (recheck en BD)."""
    ghost = _mint(str(uuid.uuid4()))
    resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {ghost}"})
    assert resp.status_code == 401


def test_deactivating_user_kills_existing_tokens(client, super_admin_headers, make_tenant):
    tenant, user = _create_tenant_user(client, super_admin_headers, make_tenant, "revocable@example.com")
    token = _login(client, "revocable@example.com", "correcthorse123").json()["access_token"]

    resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    client.patch(f"/api/v1/auth/users/{user['id']}", json={"is_active": False}, headers=super_admin_headers)

    resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_role_change_applies_to_existing_tokens(client, super_admin_headers, make_tenant):
    """El rol sale de la BD en cada request, no del claim congelado del token."""
    tenant, user = _create_tenant_user(client, super_admin_headers, make_tenant, "degradable@example.com")
    token = _login(client, "degradable@example.com", "correcthorse123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/documents",
        data={"code": "SEC-001", "title": "Doc", "document_type": "policy"},
        files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 201

    client.patch(f"/api/v1/auth/users/{user['id']}", json={"role": "viewer"}, headers=super_admin_headers)

    resp = client.post(
        "/api/v1/documents",
        data={"code": "SEC-002", "title": "Doc 2", "document_type": "policy"},
        files={"file": ("b.pdf", b"%PDF-1.4 y", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 403  # mismo token, rol nuevo


# ------------------------------------------------------------- refresh

def test_login_returns_refresh_token_and_refresh_rotates(client, super_admin_headers, make_tenant):
    _create_tenant_user(client, super_admin_headers, make_tenant, "refresher@example.com")
    body = _login(client, "refresher@example.com", "correcthorse123").json()
    assert body["expires_in"] > 0
    first_refresh = body["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert resp.status_code == 200
    rotated = resp.json()
    assert rotated["access_token"]
    assert rotated["refresh_token"] != first_refresh

    # El refresh token usado quedó revocado — rotación en cada uso.
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert resp.status_code == 401

    # El nuevo access token autentica.
    resp = client.get(
        "/api/v1/documents", headers={"Authorization": f"Bearer {rotated['access_token']}"}
    )
    assert resp.status_code == 200


def test_logout_revokes_refresh_token(client, super_admin_headers, make_tenant):
    _create_tenant_user(client, super_admin_headers, make_tenant, "logouter@example.com")
    body = _login(client, "logouter@example.com", "correcthorse123").json()

    resp = client.post("/api/v1/auth/logout", json={"refresh_token": body["refresh_token"]})
    assert resp.status_code == 204

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert resp.status_code == 401

    # Idempotente: repetir el logout no falla.
    resp = client.post("/api/v1/auth/logout", json={"refresh_token": body["refresh_token"]})
    assert resp.status_code == 204


def test_refresh_with_garbage_token_is_401(client):
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "nunca-existió"})
    assert resp.status_code == 401


# ------------------------------------------------------------- lockout

def test_account_locks_after_repeated_failures(client, super_admin_headers, make_tenant):
    _create_tenant_user(client, super_admin_headers, make_tenant, "bruteforced@example.com")

    for _ in range(settings.login_lockout_attempts):
        resp = _login(client, "bruteforced@example.com", "wrong-password")
        assert resp.status_code == 401

    # Bloqueada: ni siquiera la contraseña correcta entra.
    resp = _login(client, "bruteforced@example.com", "correcthorse123")
    assert resp.status_code == 401
    assert "bloqueada" in resp.json()["detail"].lower()


def test_successful_login_resets_failure_counter(client, super_admin_headers, make_tenant):
    _create_tenant_user(client, super_admin_headers, make_tenant, "resiliente@example.com")

    for _ in range(settings.login_lockout_attempts - 1):
        _login(client, "resiliente@example.com", "wrong-password")

    assert _login(client, "resiliente@example.com", "correcthorse123").status_code == 200
    # El contador quedó en cero: los mismos N-1 fallos de nuevo no bloquean.
    for _ in range(settings.login_lockout_attempts - 1):
        _login(client, "resiliente@example.com", "wrong-password")
    assert _login(client, "resiliente@example.com", "correcthorse123").status_code == 200


def test_login_rate_limiter_unit():
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert all(limiter.allow("1.2.3.4") for _ in range(3))
    assert not limiter.allow("1.2.3.4")
    assert limiter.allow("5.6.7.8")  # otra IP no comparte la ventana


# ----------------------------------------------------- archivos y headers

def test_upload_rejects_disallowed_extension(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = client.post(
        "/api/v1/documents",
        data={"code": "EXE-001", "title": "Malicioso", "document_type": "other"},
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 415


def test_upload_rejects_content_not_matching_extension(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = client.post(
        "/api/v1/documents",
        data={"code": "FAKE-001", "title": "PDF falso", "document_type": "other"},
        files={"file": ("no-es-pdf.pdf", b"MZ\x90\x00 ejecutable disfrazado", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 415


def test_download_serves_server_derived_content_type(client, make_tenant, auth_headers, upload_document):
    """El content_type que declara el cliente se ignora — se sirve el derivado."""
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = upload_document(
        headers, code="CT-001", filename="evidencia.pdf", content=b"%PDF-1.4 x",
        content_type="text/html",  # mentira del cliente
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


def test_oversized_content_length_is_rejected_by_middleware(client):
    limit = Settings().max_request_body_mb * 1024 * 1024
    resp = client.post(
        "/api/v1/auth/login",
        content=b"x",
        headers={"Content-Length": str(limit + 1), "Content-Type": "application/json"},
    )
    assert resp.status_code == 413


def test_security_headers_present_on_responses(client):
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


# ------------------------------------------------------------- bitácora

def test_activity_log_records_login_and_document_lifecycle(
    client, super_admin_headers, make_tenant, upload_document
):
    tenant, _ = _create_tenant_user(client, super_admin_headers, make_tenant, "trazado@example.com")
    body = _login(client, "trazado@example.com", "correcthorse123").json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    resp = upload_document(headers, code="TRZ-001")
    doc_id = resp.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers)

    resp = client.get("/api/v1/activity", headers=headers)
    assert resp.status_code == 200
    actions = [e["action"] for e in resp.json()]
    for expected in (
        "auth.login",
        "documents.created",
        "documents.submitted",
        "documents.approved",
        "documents.downloaded",
    ):
        assert expected in actions, f"falta {expected} en {actions}"


def test_activity_log_records_failed_logins(client, super_admin_headers, make_tenant, auth_headers):
    _create_tenant_user(client, super_admin_headers, make_tenant, "fallido@example.com")
    _login(client, "fallido@example.com", "wrong-password")

    # El evento de fallo no tiene tenant — se verifica directo en BD.
    from sqlalchemy import select

    from app.activity.models import ActivityEvent
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        events = db.scalars(
            select(ActivityEvent).where(
                ActivityEvent.action == "auth.login_failed",
                ActivityEvent.actor_email == "fallido@example.com",
            )
        ).all()
    assert events, "el login fallido debe quedar en la bitácora aunque el request sea 401"


def test_activity_endpoint_requires_tenant_admin(client, make_tenant, auth_headers):
    tenant = make_tenant()
    viewer = auth_headers(tenant["id"], role="viewer")
    assert client.get("/api/v1/activity", headers=viewer).status_code == 403


@pytest.mark.parametrize("env_name", ["production", "staging"])
def test_default_secret_refuses_to_start_outside_local(env_name):
    bad = Settings(environment=env_name, jwt_secret="dev-secret-change-me")
    with pytest.raises(RuntimeError):
        bad.assert_production_ready()


def test_production_config_requires_https_origins():
    bad = Settings(
        environment="production",
        jwt_secret="x" * 40,
        cors_origins="http://plaintext.example.com",
    )
    with pytest.raises(RuntimeError):
        bad.assert_production_ready()

    ok = Settings(
        environment="production",
        jwt_secret="x" * 40,
        cors_origins="https://app.tridenty.example.com",
    )
    ok.assert_production_ready()  # no debe levantar
