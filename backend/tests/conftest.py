import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

os.environ.setdefault(
    "TRIDENTY_DATABASE_URL",
    "postgresql+psycopg2://tridenty:tridenty@localhost:5432/tridentyauditor_test",
)
os.environ.setdefault("TRIDENTY_JWT_SECRET", "test-secret")
# El limitador por IP es global por proceso y el TestClient siempre llega
# como la misma IP — con el límite real, la suite entera se auto-bloquearía.
# Se desactiva aquí; su lógica se prueba directo en test_security.py.
os.environ.setdefault("TRIDENTY_LOGIN_RATE_LIMIT_PER_MINUTE", "0")
# Aislado en un directorio temporal propio del proceso de pruebas — nunca el
# ./data/documents de un checkout de desarrollo real.
os.environ.setdefault("TRIDENTY_DOCUMENTS_STORAGE_DIR", tempfile.mkdtemp(prefix="tridenty-docs-test-"))

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    """Applies alembic migrations against a real Postgres before the suite runs.

    RLS policies are Postgres-specific — these tests deliberately do not run
    against SQLite, since the whole point is verifying real tenant isolation
    (sección 06: "Aislamiento verificable... prueba automatizada").
    """
    env = os.environ.copy()
    # check=True también en el downgrade: un downgrade roto debe reventar la
    # suite, no pasar en silencio (Fase Q). Sobre una BD vacía es un no-op.
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )
    yield


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


# Un solo hash bcrypt para todos los usuarios de prueba — bcrypt es caro a
# propósito y aquí la contraseña nunca se verifica vía login.
_TEST_PASSWORD_HASH: str | None = None


def _test_password_hash() -> str:
    global _TEST_PASSWORD_HASH
    if _TEST_PASSWORD_HASH is None:
        from app.core.security import hash_password

        _TEST_PASSWORD_HASH = hash_password("test-password-123")
    return _TEST_PASSWORD_HASH


@pytest.fixture()
def token_factory():
    """Crea (o re-apunta) un usuario REAL y emite un access token suyo.

    Desde la Fase S1, cada request re-verifica la cuenta contra la BD (rol,
    tenant, is_active), así que un token con un ``sub`` inventado ya no
    autentica: el usuario tiene que existir. Si el email ya existe de un
    test anterior (la BD es compartida por la sesión), se actualiza su
    rol/tenant en vez de chocar con el unique de email.
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy import select

    from app.auth.models import User, UserRole
    from app.core.database import SessionLocal
    from app.core.security import issue_access_token

    def _make(
        tenant_id: str | None = None,
        sub: str | None = None,
        email: str | None = None,
        role: str = "tenant_admin",
        full_name: str = "Tester",
    ) -> str:
        if email is None:
            # Sin email explícito, la identidad se deriva de (rol, tenant):
            # dos tenants distintos obtienen usuarios distintos — si
            # compartieran el email, el upsert re-apuntaría el usuario al
            # segundo tenant y el token del primero autenticaría como el
            # segundo (los tests de aislamiento se romperían... con razón).
            suffix = (tenant_id or "global").replace("-", "")[:12]
            email = f"tester-{role}-{suffix}@example.com"
        with SessionLocal() as db:
            user = db.scalars(select(User).where(sa_func.lower(User.email) == email.lower())).first()
            if user is None:
                user = User(
                    id=uuid.UUID(sub) if sub else uuid.uuid4(),
                    email=email.lower(),
                    password_hash=_test_password_hash(),
                    full_name=full_name,
                    role=UserRole(role),
                    tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
                )
                db.add(user)
            else:
                user.role = UserRole(role)
                user.tenant_id = uuid.UUID(tenant_id) if tenant_id else None
                user.full_name = full_name
                user.is_active = True
            db.commit()
            token, _ = issue_access_token(user.id)
        return token

    return _make


@pytest.fixture()
def auth_headers(token_factory):
    def _make(tenant_id: str, **kwargs) -> dict[str, str]:
        return {"Authorization": f"Bearer {token_factory(tenant_id=tenant_id, **kwargs)}"}

    return _make


@pytest.fixture()
def super_admin_headers(token_factory):
    token = token_factory(tenant_id=None, role="super_admin", email="super@netmask.co", full_name="Super Admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_tenant(client, super_admin_headers):
    def _make(name: str = "Tenant de prueba", slug: str | None = None, framework_code: str = "ISO27001:2022"):
        slug = slug or f"tenant-{uuid.uuid4().hex[:8]}"
        frameworks = client.get("/api/v1/frameworks").json()
        framework_id = next(f["id"] for f in frameworks if f["code"] == framework_code)
        resp = client.post(
            "/api/v1/tenants",
            json={"name": name, "slug": slug, "framework_id": framework_id},
            headers=super_admin_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture()
def upload_document(client):
    """POST /api/v1/documents como multipart/form-data — MOD·DOC exige un
    archivo real adjunto, ya no acepta un ``storage_ref`` de texto libre."""

    def _upload(
        headers: dict[str, str],
        *,
        code: str,
        title: str = "Documento de prueba",
        document_type: str = "policy",
        control_id: str | None = None,
        retention_months: int | None = None,
        change_summary: str | None = None,
        filename: str = "evidencia.pdf",
        content: bytes = b"%PDF-1.4 contenido de prueba",
        content_type: str = "application/pdf",
    ):
        data = {"code": code, "title": title, "document_type": document_type}
        if control_id is not None:
            data["control_id"] = control_id
        if retention_months is not None:
            data["retention_months"] = str(retention_months)
        if change_summary is not None:
            data["change_summary"] = change_summary
        return client.post(
            "/api/v1/documents",
            data=data,
            files={"file": (filename, content, content_type)},
            headers=headers,
        )

    return _upload


@pytest.fixture()
def upload_version(client):
    def _upload(
        headers: dict[str, str],
        document_id: str,
        *,
        change_summary: str | None = None,
        filename: str = "evidencia-v2.pdf",
        content: bytes = b"%PDF-1.4 v2",
        content_type: str = "application/pdf",
    ):
        data = {}
        if change_summary is not None:
            data["change_summary"] = change_summary
        return client.post(
            f"/api/v1/documents/{document_id}/versions",
            data=data,
            files={"file": (filename, content, content_type)},
            headers=headers,
        )

    return _upload
