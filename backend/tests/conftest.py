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
# Aislado en un directorio temporal propio del proceso de pruebas — nunca el
# ./data/documents de un checkout de desarrollo real.
os.environ.setdefault("TRIDENTY_DOCUMENTS_STORAGE_DIR", tempfile.mkdtemp(prefix="tridenty-docs-test-"))

import jwt
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
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        env=env,
        check=False,
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


@pytest.fixture()
def token_factory():
    from app.core.config import get_settings

    settings = get_settings()

    def _make(
        tenant_id: str | None = None,
        sub: str | None = None,
        email: str = "tester@example.com",
        role: str = "tenant_admin",
        full_name: str = "Tester",
    ) -> str:
        claims = {"sub": sub or str(uuid.uuid4()), "email": email, "full_name": full_name, "role": role}
        if tenant_id is not None:
            claims["tenant_id"] = tenant_id
        return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

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
