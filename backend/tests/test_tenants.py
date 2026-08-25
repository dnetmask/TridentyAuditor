def _iso_framework_id(client):
    frameworks = client.get("/api/v1/frameworks").json()
    return next(f["id"] for f in frameworks if f["code"] == "ISO27001:2022")


def _cno_framework_id(client):
    frameworks = client.get("/api/v1/frameworks").json()
    return next(f["id"] for f in frameworks if f["code"] == "CNO-1960")


def test_create_tenant_requires_framework_id(client, super_admin_headers):
    resp = client.post(
        "/api/v1/tenants",
        json={"name": "Sin norma", "slug": "sin-norma"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 422


def test_create_tenant_with_unknown_framework_id_is_404(client, super_admin_headers):
    resp = client.post(
        "/api/v1/tenants",
        json={
            "name": "Norma inexistente",
            "slug": "norma-inexistente",
            "framework_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 404


def test_create_tenant_with_cno1960_framework(client, super_admin_headers):
    resp = client.post(
        "/api/v1/tenants",
        json={
            "name": "Empresa del sector eléctrico",
            "slug": "empresa-electrica",
            "framework_id": _cno_framework_id(client),
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["framework"]["code"] == "CNO-1960"


def test_tenant_read_embeds_framework(client, super_admin_headers):
    resp = client.post(
        "/api/v1/tenants",
        json={
            "name": "Empresa ISO",
            "slug": "empresa-iso",
            "framework_id": _iso_framework_id(client),
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 201, resp.text
    tenant_id = resp.json()["id"]

    resp = client.get(f"/api/v1/tenants/{tenant_id}", headers=super_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["framework"]["code"] == "ISO27001:2022"


def test_login_response_carries_tenant_framework_code(client, super_admin_headers):
    tenant_resp = client.post(
        "/api/v1/tenants",
        json={
            "name": "Empresa login",
            "slug": "empresa-login",
            "framework_id": _cno_framework_id(client),
        },
        headers=super_admin_headers,
    )
    tenant_id = tenant_resp.json()["id"]
    resp = client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin@empresa-login.co",
            "password": "supersecret123",
            "full_name": "Admin CNO",
            "role": "tenant_admin",
            "tenant_id": tenant_id,
        },
        headers=super_admin_headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@empresa-login.co", "password": "supersecret123"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["framework_code"] == "CNO-1960"


def test_super_admin_login_has_no_framework_code(client):
    import uuid

    from app.auth.service import bootstrap_super_admin
    from app.core.database import SessionLocal

    email = f"super-fase0-{uuid.uuid4().hex[:8]}@netmask.co"
    db = SessionLocal()
    try:
        bootstrap_super_admin(db, email=email, password="supersecret123", full_name="Root")
    finally:
        db.close()

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["framework_code"] is None
