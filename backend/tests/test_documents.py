def test_document_lifecycle_and_controlled_copies(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], email="ciso@example.com")

    resp = client.post(
        "/api/v1/documents",
        json={
            "code": "POL-001",
            "title": "Política de seguridad de la información",
            "document_type": "policy",
            "storage_ref": "s3://bucket/pol-001-v1.pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    doc_id = doc["id"]
    assert doc["versions"][0]["version_number"] == 1
    assert doc["versions"][0]["status"] == "draft"
    assert doc["versions"][0]["created_by"] == "ciso@example.com"

    # Can't approve straight from draft.
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 409

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_review"

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["approved_by"] == "ciso@example.com"

    # A second draft opens, goes through review, and approving it must
    # obsolete v1 — only one controlled copy is current at a time.
    resp = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        json={"storage_ref": "s3://bucket/pol-001-v2.pdf"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["version_number"] == 2

    client.post(f"/api/v1/documents/{doc_id}/versions/2/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/2/approve", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    statuses = {v["version_number"]: v["status"] for v in resp.json()["versions"]}
    assert statuses == {1: "obsolete", 2: "approved"}


def test_cannot_open_second_draft_while_one_is_open(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = client.post(
        "/api/v1/documents",
        json={
            "code": "POL-002",
            "title": "Otra política",
            "document_type": "policy",
            "storage_ref": "s3://bucket/x",
        },
        headers=headers,
    )
    doc_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        json={"storage_ref": "s3://bucket/x-v2"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_documents_require_auth(client):
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 401


def test_viewer_cannot_create_documents(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], role="viewer")
    resp = client.post(
        "/api/v1/documents",
        json={"code": "POL-003", "title": "X", "document_type": "policy", "storage_ref": "s3://x"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_internal_auditor_can_create_and_submit_but_not_approve(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], role="internal_auditor", email="auditor@example.com")

    resp = client.post(
        "/api/v1/documents",
        json={
            "code": "AUD-001",
            "title": "Programa de auditoría",
            "document_type": "record",
            "storage_ref": "s3://x",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 403
