def test_tenant_cannot_read_another_tenants_documents(client, make_tenant, auth_headers):
    """Sección 06: aislamiento verificable — RLS real, no un filtro en código.

    Si alguien borrara el `.where(Document.tenant_id == tenant_id)` del
    service layer, esta prueba seguiría pasando porque la política de
    Postgres es la que filtra, no el ORM.
    """
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    headers_a = auth_headers(tenant_a["id"])
    headers_b = auth_headers(tenant_b["id"])

    resp = client.post(
        "/api/v1/documents",
        json={
            "code": "POL-ISO",
            "title": "Solo visible para el tenant A",
            "document_type": "policy",
            "storage_ref": "s3://a",
            "created_by": "tester",
        },
        headers=headers_a,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = client.get("/api/v1/documents", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.get(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert resp.status_code == 404

    resp = client.get(f"/api/v1/documents/{doc_id}", headers=headers_a)
    assert resp.status_code == 200


def test_tenants_can_reuse_document_codes(client, make_tenant, auth_headers):
    """El unique constraint es (tenant_id, code) — dos tenants pueden usar el mismo código."""
    tenant_a = make_tenant()
    tenant_b = make_tenant()

    payload = {
        "code": "POL-SAME",
        "title": "Mismo código, tenants distintos",
        "document_type": "policy",
        "storage_ref": "s3://same",
        "created_by": "tester",
    }
    resp_a = client.post("/api/v1/documents", json=payload, headers=auth_headers(tenant_a["id"]))
    resp_b = client.post("/api/v1/documents", json=payload, headers=auth_headers(tenant_b["id"]))
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
