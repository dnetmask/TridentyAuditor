import os
import subprocess
import sys
import uuid
from pathlib import Path

os.environ.setdefault(
    "TRIDENTY_DATABASE_URL",
    "postgresql+psycopg2://tridenty:tridenty@localhost:5432/tridentyauditor_test",
)
os.environ.setdefault("TRIDENTY_JWT_SECRET", "test-secret")

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
    def _make(name: str = "Tenant de prueba", slug: str | None = None):
        slug = slug or f"tenant-{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/v1/tenants", json={"name": name, "slug": slug}, headers=super_admin_headers
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make
