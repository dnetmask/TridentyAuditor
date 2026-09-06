"""Fase 5a: acuse de recibo (leído y entendido) y retención/disposición final."""


def _approve(client, headers, doc_id, version=1):
    client.post(f"/api/v1/documents/{doc_id}/versions/{version}/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/{version}/approve", headers=headers)
    assert resp.status_code == 200, resp.text


def _directory_ids(client, headers):
    return [u["id"] for u in client.get("/api/v1/auth/directory", headers=headers).json()]


# ------------------------------------------------------------ acuse de recibo

def test_publish_requires_approved_version(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-500").json()
    users = _directory_ids(client, admin)

    # Sin versión aprobada → 409.
    resp = client.post(f"/api/v1/documents/{doc['id']}/publish", json={"user_ids": users}, headers=admin)
    assert resp.status_code == 409

    _approve(client, admin, doc["id"])
    resp = client.post(f"/api/v1/documents/{doc['id']}/publish", json={"user_ids": users}, headers=admin)
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert summary["total"] == len(users)
    assert summary["pending"] == len(users)
    assert summary["acknowledged"] == 0


def test_acknowledge_marks_read_and_updates_summary(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    # Un segundo usuario del tenant (auditor) al que se le distribuye.
    reader = auth_headers(tenant["id"], role="internal_auditor", email="lector@example.com", full_name="Lector")
    reader_id = next(
        u["id"] for u in client.get("/api/v1/auth/directory", headers=admin).json()
        if u["full_name"] == "Lector"
    )

    doc = upload_document(admin, code="POL-501").json()
    _approve(client, admin, doc["id"])
    client.post(f"/api/v1/documents/{doc['id']}/publish", json={"user_ids": [reader_id]}, headers=admin)

    # El lector ve el documento en "mis pendientes".
    pending = client.get("/api/v1/documents/my-acknowledgments", headers=reader).json()
    assert any(p["document_id"] == doc["id"] for p in pending)

    # Marca leído y entendido.
    resp = client.post(f"/api/v1/documents/{doc['id']}/acknowledge", headers=reader)
    assert resp.status_code == 200, resp.text
    assert resp.json()["acknowledged_at"] is not None

    # Ya no está pendiente; el resumen lo cuenta como leído.
    assert client.get("/api/v1/documents/my-acknowledgments", headers=reader).json() == []
    summary = client.get(f"/api/v1/documents/{doc['id']}/acknowledgments", headers=admin).json()
    assert summary["acknowledged"] == 1
    assert summary["pending"] == 0


def test_publish_is_idempotent_and_validates_users(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    other = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-502").json()
    _approve(client, admin, doc["id"])
    users = _directory_ids(client, admin)

    client.post(f"/api/v1/documents/{doc['id']}/publish", json={"user_ids": users}, headers=admin)
    # Republicar a los mismos no duplica.
    summary = client.post(
        f"/api/v1/documents/{doc['id']}/publish", json={"user_ids": users}, headers=admin
    ).json()
    assert summary["total"] == len(users)

    # Un usuario de otro tenant → 422.
    foreign = _directory_ids(client, auth_headers(other["id"]))
    resp = client.post(
        f"/api/v1/documents/{doc['id']}/publish", json={"user_ids": foreign}, headers=admin
    )
    assert resp.status_code == 422


def test_acknowledge_without_assignment_is_404(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-503").json()
    _approve(client, admin, doc["id"])
    # Nadie le asignó acuse al admin de este doc.
    assert client.post(f"/api/v1/documents/{doc['id']}/acknowledge", headers=admin).status_code == 404


# ------------------------------------------------------ retención / disposición

def test_disposition_date_computed_from_retention(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="REG-500", retention_months=12).json()
    _approve(client, admin, doc["id"])

    detail = client.get(f"/api/v1/documents/{doc['id']}", headers=admin).json()
    assert detail["disposition_date"] is not None  # aprobado + 12 meses

    # Sin retención, no vence.
    doc2 = upload_document(admin, code="REG-501").json()
    _approve(client, admin, doc2["id"])
    detail2 = client.get(f"/api/v1/documents/{doc2['id']}", headers=admin).json()
    assert detail2["disposition_date"] is None


def test_legal_hold_blocks_disposition(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="REG-502", retention_months=1).json()
    _approve(client, admin, doc["id"])

    # Activar retención legal.
    resp = client.post(f"/api/v1/documents/{doc['id']}/legal-hold", json={"hold": True}, headers=admin)
    assert resp.status_code == 200
    assert resp.json()["legal_hold"] is True

    # Disponer está bloqueado.
    resp = client.post(
        f"/api/v1/documents/{doc['id']}/dispose",
        json={"action": "archive", "notes": "fin de retención"},
        headers=admin,
    )
    assert resp.status_code == 409

    # Levantar el hold y disponer (destruir) con acta.
    client.post(f"/api/v1/documents/{doc['id']}/legal-hold", json={"hold": False}, headers=admin)
    resp = client.post(
        f"/api/v1/documents/{doc['id']}/dispose",
        json={"action": "destroy", "notes": "Destrucción autorizada por el comité"},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    disposed = resp.json()
    assert disposed["disposition_action"] == "destroy"
    assert disposed["disposed_by"] is not None

    # No se puede disponer dos veces.
    assert client.post(
        f"/api/v1/documents/{doc['id']}/dispose",
        json={"action": "archive", "notes": "otra vez"},
        headers=admin,
    ).status_code == 409


def test_acknowledgments_isolated_per_tenant(
    client, make_tenant, auth_headers, upload_document
):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    admin_a = auth_headers(tenant_a["id"])
    doc = upload_document(admin_a, code="POL-504").json()
    _approve(client, admin_a, doc["id"])
    client.post(
        f"/api/v1/documents/{doc['id']}/publish",
        json={"user_ids": _directory_ids(client, admin_a)},
        headers=admin_a,
    )
    # El tenant B no ve ni el documento ni sus acuses.
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers(tenant_b["id"])).status_code == 404
