"""Dashboard de entrada (Fase 4): agregado del estado del tenant."""


def _submit_approve(client, headers, doc_id):
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)


def test_dashboard_shape_and_empty_tenant(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    data = client.get("/api/v1/dashboard/overview", headers=admin).json()

    for key in ("compliance", "documents", "risks", "audits", "legal", "soa", "processes"):
        assert key in data
    assert data["documents"]["total_vigentes"] == 0
    assert data["processes"]["total"] == 0
    assert data["compliance"]["percentage"] == 0.0


def test_dashboard_counts_reflect_real_state(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])

    # Dos documentos: uno aprobado vigente, otro en revisión.
    approved = upload_document(admin, code="POL-DSH-1").json()
    _submit_approve(client, admin, approved["id"])
    in_review = upload_document(admin, code="POL-DSH-2").json()
    client.post(f"/api/v1/documents/{in_review['id']}/versions/1/submit", headers=admin)

    # Un proceso, un requisito legal, un riesgo.
    client.post("/api/v1/processes", json={"name": "Proceso DSH"}, headers=admin)
    client.post(
        "/api/v1/legal-requirements",
        json={"requirement_type": "law", "name": "Ley DSH"},
        headers=admin,
    )
    risk_resp = client.post(
        "/api/v1/risk/risks",
        json={"title": "Riesgo DSH", "likelihood": 3, "impact": 4},
        headers=admin,
    )
    assert risk_resp.status_code == 201, risk_resp.text

    data = client.get("/api/v1/dashboard/overview", headers=admin).json()
    assert data["documents"]["total_vigentes"] == 2
    assert data["documents"]["pending_approval"] == 1
    assert data["processes"]["total"] == 1
    assert data["legal"]["total"] == 1
    assert data["risks"]["total"] == 1
    assert data["risks"]["open"] == 1


def test_dashboard_is_isolated_per_tenant(
    client, make_tenant, auth_headers, upload_document
):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    upload_document(auth_headers(tenant_a["id"]), code="POL-DSH-A")

    data_b = client.get("/api/v1/dashboard/overview", headers=auth_headers(tenant_b["id"])).json()
    assert data_b["documents"]["total_vigentes"] == 0
