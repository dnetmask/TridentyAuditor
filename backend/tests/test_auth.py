from app.core.security import hash_password


def test_login_success_and_failure(client, make_tenant, super_admin_headers):
    tenant = make_tenant()
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "login-test@example.com",
            "password": "correcthorse123",
            "full_name": "Login Test",
            "role": "tenant_admin",
            "tenant_id": tenant["id"],
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "login-test@example.com", "password": "correcthorse123"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "tenant_admin"
    assert body["tenant_id"] == tenant["id"]
    assert body["tenant_name"] == tenant["name"]
    assert "access_token" in body

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "login-test@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401


def test_inactive_user_cannot_login(client, make_tenant, super_admin_headers):
    tenant = make_tenant()
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "inactive@example.com",
            "password": "correcthorse123",
            "full_name": "Inactive",
            "role": "viewer",
            "tenant_id": tenant["id"],
        },
        headers=super_admin_headers,
    )
    user_id = resp.json()["id"]

    client.patch(f"/api/v1/auth/users/{user_id}", json={"is_active": False}, headers=super_admin_headers)

    resp = client.post(
        "/api/v1/auth/login", json={"email": "inactive@example.com", "password": "correcthorse123"}
    )
    assert resp.status_code == 401


def test_super_admin_can_create_users_for_any_tenant(client, make_tenant, super_admin_headers):
    tenant = make_tenant()
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "auditor@example.com",
            "password": "correcthorse123",
            "full_name": "Auditor",
            "role": "internal_auditor",
            "tenant_id": tenant["id"],
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["tenant_id"] == tenant["id"]


def test_super_admin_account_rejects_tenant_id(client, make_tenant, super_admin_headers):
    tenant = make_tenant()
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "bad-super@example.com",
            "password": "correcthorse123",
            "full_name": "Bad Super",
            "role": "super_admin",
            "tenant_id": tenant["id"],
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


def test_tenant_admin_cannot_create_super_admin(client, make_tenant, super_admin_headers, auth_headers):
    tenant = make_tenant()
    tenant_admin_headers = auth_headers(tenant["id"], role="tenant_admin", email="admin@tenant.com")

    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "wannabe-super@example.com",
            "password": "correcthorse123",
            "full_name": "Wannabe",
            "role": "super_admin",
        },
        headers=tenant_admin_headers,
    )
    assert resp.status_code == 403


def test_tenant_admin_is_forced_into_own_tenant_regardless_of_payload(
    client, make_tenant, super_admin_headers, auth_headers
):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    admin_a_headers = auth_headers(tenant_a["id"], role="tenant_admin", email="admin-a@example.com")

    # Tries to sneak a user into tenant B while authenticated as tenant A's admin.
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "sneaky@example.com",
            "password": "correcthorse123",
            "full_name": "Sneaky",
            "role": "viewer",
            "tenant_id": tenant_b["id"],
        },
        headers=admin_a_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["tenant_id"] == tenant_a["id"]  # ignored the payload's tenant_id


def test_tenant_admin_cannot_see_or_edit_users_of_another_tenant(
    client, make_tenant, super_admin_headers, auth_headers
):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    admin_a_headers = auth_headers(tenant_a["id"], role="tenant_admin", email="admin-a2@example.com")

    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "viewer-b@example.com",
            "password": "correcthorse123",
            "full_name": "Viewer B",
            "role": "viewer",
            "tenant_id": tenant_b["id"],
        },
        headers=super_admin_headers,
    )
    user_b_id = resp.json()["id"]

    resp = client.get("/api/v1/auth/users", headers=admin_a_headers)
    assert resp.status_code == 200
    assert all(u["id"] != user_b_id for u in resp.json())

    resp = client.patch(
        f"/api/v1/auth/users/{user_b_id}", json={"full_name": "Hacked"}, headers=admin_a_headers
    )
    assert resp.status_code == 404


def test_viewer_and_internal_auditor_cannot_manage_users(client, make_tenant, auth_headers):
    tenant = make_tenant()
    viewer_headers = auth_headers(tenant["id"], role="viewer")
    auditor_headers = auth_headers(tenant["id"], role="internal_auditor")

    payload = {
        "email": "new-user@example.com",
        "password": "correcthorse123",
        "full_name": "New User",
        "role": "viewer",
        "tenant_id": tenant["id"],
    }
    assert client.post("/api/v1/auth/users", json=payload, headers=viewer_headers).status_code == 403
    assert client.post("/api/v1/auth/users", json=payload, headers=auditor_headers).status_code == 403


def test_super_admin_token_cannot_access_tenant_scoped_endpoints(client, super_admin_headers):
    resp = client.get("/api/v1/documents", headers=super_admin_headers)
    assert resp.status_code == 401

    resp = client.get("/api/v1/wizard/progress", headers=super_admin_headers)
    assert resp.status_code == 401


def test_me_endpoint_reflects_token_claims(client, auth_headers, make_tenant):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], role="internal_auditor", email="me@example.com", full_name="Me Myself")
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["role"] == "internal_auditor"
    assert body["tenant_id"] == tenant["id"]
    assert body["full_name"] == "Me Myself"


def test_password_hash_roundtrip():
    from app.core.security import verify_password

    hashed = hash_password("correcthorse123")
    assert hashed != "correcthorse123"
    assert verify_password("correcthorse123", hashed)
    assert not verify_password("wrong", hashed)


def test_bootstrap_super_admin_noop_without_env_vars():
    from app.auth.service import bootstrap_super_admin
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        bootstrap_super_admin(db, email=None, password=None, full_name="Super Admin")
    finally:
        db.close()


def test_bootstrap_super_admin_creates_account_once():
    import uuid

    from app.auth.models import User
    from app.auth.service import bootstrap_super_admin
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        email = f"bootstrap-{uuid.uuid4().hex[:8]}@netmask.co"
        bootstrap_super_admin(db, email=email, password="supersecret123", full_name="Root")
        user = db.query(User).filter_by(email=email).one()
        assert user.role.value == "super_admin"
        assert user.tenant_id is None

        # Idempotente: correrlo de nuevo (ej. reinicios del contenedor) no falla ni duplica.
        bootstrap_super_admin(db, email=email, password="otra-cosa-distinta", full_name="Root")
        assert db.query(User).filter_by(email=email).count() == 1
    finally:
        db.close()


def test_bootstrap_super_admin_requires_both_vars_together():
    import pytest

    from app.auth.service import InvalidUser, bootstrap_super_admin
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        with pytest.raises(InvalidUser):
            bootstrap_super_admin(db, email="solo-email@netmask.co", password=None, full_name="Root")
        with pytest.raises(InvalidUser):
            bootstrap_super_admin(db, email=None, password="solo-password", full_name="Root")
    finally:
        db.close()
