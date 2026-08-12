def _approve_document(client, headers, code="EVID-001"):
    resp = client.post(
        "/api/v1/documents",
        json={
            "code": code,
            "title": "Evidencia de prueba",
            "document_type": "record",
            "storage_ref": "s3://bucket/evid.pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    return doc_id


def test_overview_is_zero_before_soa_or_wizard_start(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    resp = client.get("/api/v1/compliance/overview", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["percentage"] == 0.0
    by_key = {c["key"]: c for c in data["components"]}
    assert by_key["soa"] == {"key": "soa", "label": by_key["soa"]["label"], "evidenced": 0, "total": 0, "percentage": 0.0}
    assert by_key["wizard"]["total"] == 0


def test_linking_approved_evidence_to_soa_entry_raises_percentage(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    client.post("/api/v1/soa/instantiate", headers=headers)
    entries = client.get("/api/v1/soa/entries", headers=headers).json()
    doc_id = _approve_document(client, headers)

    resp = client.patch(
        f"/api/v1/soa/entries/{entries[0]['id']}",
        json={"evidence_document_id": doc_id},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/compliance/overview", headers=headers)
    data = resp.json()
    soa = next(c for c in data["components"] if c["key"] == "soa")
    assert soa["evidenced"] == 1
    assert soa["total"] == 93
    assert soa["percentage"] > 0
    assert data["percentage"] > 0


def test_unapproved_evidence_does_not_count(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    client.post("/api/v1/soa/instantiate", headers=headers)
    entries = client.get("/api/v1/soa/entries", headers=headers).json()

    resp = client.post(
        "/api/v1/documents",
        json={
            "code": "DRAFT-001",
            "title": "Sin aprobar",
            "document_type": "record",
            "storage_ref": "s3://bucket/draft.pdf",
        },
        headers=headers,
    )
    draft_doc_id = resp.json()["id"]
    client.patch(
        f"/api/v1/soa/entries/{entries[0]['id']}",
        json={"evidence_document_id": draft_doc_id},
        headers=headers,
    )

    resp = client.get("/api/v1/compliance/overview", headers=headers)
    soa = next(c for c in resp.json()["components"] if c["key"] == "soa")
    assert soa["evidenced"] == 0


def test_completing_wizard_task_with_evidence_raises_percentage(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    client.post("/api/v1/wizard/instantiate", headers=headers)
    progress = client.get("/api/v1/wizard/progress", headers=headers).json()
    task = next(t for t in progress[0]["tasks"] if t["requires_evidence"])
    doc_id = _approve_document(client, headers)
    client.patch(
        f"/api/v1/wizard/tasks/{task['id']}", json={"evidence_document_id": doc_id}, headers=headers
    )
    resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/compliance/overview", headers=headers)
    data = resp.json()
    wizard = next(c for c in data["components"] if c["key"] == "wizard")
    assert wizard["evidenced"] == 1
    assert data["percentage"] > 0


def test_viewer_can_read_overview(client, make_tenant, auth_headers):
    tenant = make_tenant()
    viewer_headers = auth_headers(tenant["id"], role="viewer")
    resp = client.get("/api/v1/compliance/overview", headers=viewer_headers)
    assert resp.status_code == 200


def test_overview_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    headers_a = auth_headers(tenant_a["id"])
    headers_b = auth_headers(tenant_b["id"])

    client.post("/api/v1/soa/instantiate", headers=headers_a)
    entries_a = client.get("/api/v1/soa/entries", headers=headers_a).json()
    doc_id = _approve_document(client, headers_a)
    client.patch(
        f"/api/v1/soa/entries/{entries_a[0]['id']}",
        json={"evidence_document_id": doc_id},
        headers=headers_a,
    )

    resp_b = client.get("/api/v1/compliance/overview", headers=headers_b)
    assert resp_b.json()["percentage"] == 0.0
