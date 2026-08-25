"""Fase Q: endpoints que existían sin ningún test — reject de versiones,
PATCH de activos, directorio del tenant, lista de tenants y /health."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_reject_version_returns_to_draft(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc_id = upload_document(headers, code="REJ-001").json()["id"]

    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/reject", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"

    # Rechazar algo que no está en revisión es 409, no un no-op silencioso.
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/reject", headers=headers)
    assert resp.status_code == 409


def test_reject_requires_tenant_admin(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    auditor = auth_headers(tenant["id"], role="internal_auditor")
    doc_id = upload_document(admin, code="REJ-002").json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=admin)

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/reject", headers=auditor)
    assert resp.status_code == 403


def test_patch_asset_updates_fields(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = client.post(
        "/api/v1/risk/assets",
        json={"name": "Servidor de BD", "category": "hardware"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    asset_id = resp.json()["id"]

    resp = client.patch(
        f"/api/v1/risk/assets/{asset_id}",
        json={"name": "Servidor de BD principal"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Servidor de BD principal"


def test_directory_lists_active_tenant_users_for_any_role(client, make_tenant, auth_headers):
    tenant = make_tenant()
    # Crear identidades del tenant (la factory upsertea usuarios reales).
    auth_headers(tenant["id"], email="dir-admin@example.com", full_name="Admin Dir")
    viewer_headers = auth_headers(tenant["id"], role="viewer", email="dir-viewer@example.com", full_name="Viewer Dir")

    resp = client.get("/api/v1/auth/directory", headers=viewer_headers)
    assert resp.status_code == 200
    names = [u["full_name"] for u in resp.json()]
    assert "Admin Dir" in names and "Viewer Dir" in names


def test_list_tenants_requires_super_admin_and_embeds_framework(
    client, super_admin_headers, make_tenant, auth_headers
):
    tenant = make_tenant(name="Tenant Listable")
    resp = client.get("/api/v1/tenants", headers=super_admin_headers)
    assert resp.status_code == 200
    listed = next(t for t in resp.json() if t["id"] == tenant["id"])
    assert listed["framework"]["code"] == "ISO27001:2022"

    tenant_admin = auth_headers(tenant["id"])
    assert client.get("/api/v1/tenants", headers=tenant_admin).status_code == 403
