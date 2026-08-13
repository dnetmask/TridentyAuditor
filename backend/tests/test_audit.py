def _approve_document(client, headers, code="EVID-001"):
    resp = client.post(
        "/api/v1/documents",
        data={"code": code, "title": "Evidencia de prueba", "document_type": "record"},
        files={"file": ("evidencia.pdf", b"%PDF-1.4 evidencia", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    return doc_id


def _domain_id(client, headers):
    resp = client.get("/api/v1/frameworks/ISO27001:2022/domains")
    return resp.json()[0]["id"]


def test_create_and_list_audit_program(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    domain_id = _domain_id(client, headers)

    resp = client.post(
        "/api/v1/audit/programs",
        json={
            "title": "Auditoría interna A.5 — Q1 2026",
            "scope": "Controles organizacionales",
            "domain_id": domain_id,
            "planned_date": "2026-03-01",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Auditoría interna A.5 — Q1 2026"
    assert body["status"] == "planned"
    assert body["domain"]["code"] == "A.5"

    resp = client.get("/api/v1/audit/programs", headers=headers)
    assert len(resp.json()) == 1


def test_update_program_status_and_dates(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = client.post(
        "/api/v1/audit/programs", json={"title": "Auditoría general"}, headers=headers
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/audit/programs/{program_id}",
        json={"status": "completed", "executed_date": "2026-03-15"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"
    assert resp.json()["executed_date"] == "2026-03-15"


def test_create_finding_under_program(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = client.post(
        "/api/v1/audit/programs", json={"title": "Auditoría general"}, headers=headers
    ).json()["id"]
    control_id = client.get("/api/v1/frameworks/ISO27001:2022/domains").json()[0]["controls"][0]["id"]

    resp = client.post(
        "/api/v1/audit/findings",
        json={
            "audit_id": program_id,
            "control_id": control_id,
            "classification": "minor_nc",
            "description": "No se encontró evidencia de revisión de accesos trimestral",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["classification"] == "minor_nc"
    assert body["control"]["code"] == "A.5.1"

    resp = client.get(f"/api/v1/audit/findings?audit_id={program_id}", headers=headers)
    assert len(resp.json()) == 1


def test_finding_under_unknown_program_returns_404(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = client.post(
        "/api/v1/audit/findings",
        json={
            "audit_id": "00000000-0000-0000-0000-000000000000",
            "classification": "observation",
            "description": "x",
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_closing_finding_requires_approved_evidence(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = client.post(
        "/api/v1/audit/programs", json={"title": "Auditoría general"}, headers=headers
    ).json()["id"]
    finding_id = client.post(
        "/api/v1/audit/findings",
        json={"audit_id": program_id, "classification": "major_nc", "description": "Hallazgo grave"},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/audit/findings/{finding_id}", json={"status": "closed"}, headers=headers
    )
    assert resp.status_code == 422

    draft_doc = client.post(
        "/api/v1/documents",
        data={"code": "CAPA-DRAFT-001", "title": "Plan sin aprobar", "document_type": "record"},
        files={"file": ("draft.pdf", b"%PDF-1.4 draft", "application/pdf")},
        headers=headers,
    ).json()["id"]
    resp = client.patch(
        f"/api/v1/audit/findings/{finding_id}",
        json={"status": "closed", "evidence_document_id": draft_doc},
        headers=headers,
    )
    assert resp.status_code == 422

    approved_doc = _approve_document(client, headers, code="CAPA-APPROVED-001")
    resp = client.patch(
        f"/api/v1/audit/findings/{finding_id}",
        json={"status": "closed", "evidence_document_id": approved_doc},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "closed"
    assert body["closed_at"] is not None


def test_reopening_finding_clears_closed_at(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = client.post(
        "/api/v1/audit/programs", json={"title": "Auditoría general"}, headers=headers
    ).json()["id"]
    finding_id = client.post(
        "/api/v1/audit/findings",
        json={"audit_id": program_id, "classification": "observation", "description": "Observación menor"},
        headers=headers,
    ).json()["id"]
    approved_doc = _approve_document(client, headers)
    client.patch(
        f"/api/v1/audit/findings/{finding_id}",
        json={"status": "closed", "evidence_document_id": approved_doc},
        headers=headers,
    )

    resp = client.patch(
        f"/api/v1/audit/findings/{finding_id}", json={"status": "open"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is None


def test_summary_counts(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = client.post(
        "/api/v1/audit/programs", json={"title": "Auditoría general"}, headers=headers
    ).json()["id"]
    client.post(
        "/api/v1/audit/findings",
        json={"audit_id": program_id, "classification": "major_nc", "description": "a"},
        headers=headers,
    )
    client.post(
        "/api/v1/audit/findings",
        json={"audit_id": program_id, "classification": "minor_nc", "description": "b"},
        headers=headers,
    )

    resp = client.get("/api/v1/audit/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_programs"] == 1
    assert body["total_findings"] == 2
    assert body["open_findings"] == 2
    assert body["major_nc"] == 1
    assert body["minor_nc"] == 1


def test_viewer_cannot_write_audit(client, make_tenant, auth_headers):
    tenant = make_tenant()
    viewer_headers = auth_headers(tenant["id"], role="viewer")
    resp = client.post("/api/v1/audit/programs", json={"title": "X"}, headers=viewer_headers)
    assert resp.status_code == 403


def test_internal_auditor_can_manage_findings(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin_headers = auth_headers(tenant["id"])
    auditor_headers = auth_headers(tenant["id"], role="internal_auditor")

    program_id = client.post(
        "/api/v1/audit/programs", json={"title": "Auditoría general"}, headers=auditor_headers
    ).json()["id"]
    assert program_id

    resp = client.post(
        "/api/v1/audit/findings",
        json={"audit_id": program_id, "classification": "observation", "description": "x"},
        headers=auditor_headers,
    )
    assert resp.status_code == 201


def test_programs_and_findings_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    headers_a = auth_headers(tenant_a["id"])
    headers_b = auth_headers(tenant_b["id"])

    client.post("/api/v1/audit/programs", json={"title": "Solo A"}, headers=headers_a)

    assert client.get("/api/v1/audit/programs", headers=headers_b).json() == []
    assert client.get("/api/v1/audit/findings", headers=headers_b).json() == []
