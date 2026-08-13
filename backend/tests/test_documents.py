def test_document_lifecycle_and_controlled_copies(client, make_tenant, auth_headers, upload_document, upload_version):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], email="ciso@example.com")

    resp = upload_document(
        headers,
        code="POL-001",
        title="Política de seguridad de la información",
        document_type="policy",
        filename="politica-v1.pdf",
        content=b"%PDF-1.4 v1",
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    doc_id = doc["id"]
    assert doc["versions"][0]["version_number"] == 1
    assert doc["versions"][0]["status"] == "draft"
    assert doc["versions"][0]["created_by"] == "ciso@example.com"
    assert doc["versions"][0]["original_filename"] == "politica-v1.pdf"
    assert doc["versions"][0]["content_type"] == "application/pdf"
    assert doc["versions"][0]["file_size"] == len(b"%PDF-1.4 v1")

    # El binario subido se puede descargar de vuelta tal cual.
    resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers)
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 v1"
    assert resp.headers["content-type"] == "application/pdf"
    assert "politica-v1.pdf" in resp.headers["content-disposition"]

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
    resp = upload_version(headers, doc_id, filename="politica-v2.pdf", content=b"%PDF-1.4 v2")
    assert resp.status_code == 201
    assert resp.json()["version_number"] == 2

    client.post(f"/api/v1/documents/{doc_id}/versions/2/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/2/approve", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    statuses = {v["version_number"]: v["status"] for v in resp.json()["versions"]}
    assert statuses == {1: "obsolete", 2: "approved"}

    # Ambas versiones siguen descargables de forma independiente.
    resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers)
    assert resp.content == b"%PDF-1.4 v1"
    resp = client.get(f"/api/v1/documents/{doc_id}/versions/2/file", headers=headers)
    assert resp.content == b"%PDF-1.4 v2"


def test_cannot_open_second_draft_while_one_is_open(client, make_tenant, auth_headers, upload_document, upload_version):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = upload_document(headers, code="POL-002", title="Otra política")
    doc_id = resp.json()["id"]

    resp = upload_version(headers, doc_id)
    assert resp.status_code == 409


def test_documents_require_auth(client):
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 401


def test_viewer_cannot_create_documents(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], role="viewer")
    resp = upload_document(headers, code="POL-003", title="X")
    assert resp.status_code == 403


def test_internal_auditor_can_create_and_submit_but_not_approve(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"], role="internal_auditor", email="auditor@example.com")

    resp = upload_document(headers, code="AUD-001", title="Programa de auditoría", document_type="record")
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 403


def test_empty_file_is_rejected(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = upload_document(headers, code="POL-004", title="Vacío", content=b"")
    assert resp.status_code == 400


def test_oversized_file_is_rejected(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    from app.core.config import get_settings

    limit = get_settings().documents_max_file_size_mb * 1024 * 1024
    resp = upload_document(headers, code="POL-005", title="Muy grande", content=b"0" * (limit + 1))
    assert resp.status_code == 413


def test_download_requires_tenant_membership(client, make_tenant, auth_headers, upload_document):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    headers_a = auth_headers(tenant_a["id"])
    headers_b = auth_headers(tenant_b["id"])

    resp = upload_document(headers_a, code="POL-006", title="Confidencial de A")
    doc_id = resp.json()["id"]

    resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers_b)
    assert resp.status_code == 404

    resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers_a)
    assert resp.status_code == 200


def test_download_missing_version_number_is_404(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = upload_document(headers, code="POL-007", title="X")
    doc_id = resp.json()["id"]

    resp = client.get(f"/api/v1/documents/{doc_id}/versions/99/file", headers=headers)
    assert resp.status_code == 404
