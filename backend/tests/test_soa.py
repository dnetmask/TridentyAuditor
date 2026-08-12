def test_instantiate_creates_93_entries_and_is_idempotent(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    resp = client.post("/api/v1/soa/instantiate", headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"] == 93

    resp = client.post("/api/v1/soa/instantiate", headers=headers)
    assert resp.json()["created"] == 0

    resp = client.get("/api/v1/soa/entries", headers=headers)
    entries = resp.json()
    assert len(entries) == 93
    assert all(e["is_applicable"] for e in entries)
    assert all(e["implementation_status"] == "not_started" for e in entries)
    # domain/control come through nested and ordered
    assert entries[0]["control"]["domain"]["code"] == "A.5"
    assert entries[0]["control"]["code"] == "A.5.1"


def test_excluding_control_requires_justification(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    client.post("/api/v1/soa/instantiate", headers=headers)
    entry_id = client.get("/api/v1/soa/entries", headers=headers).json()[0]["id"]

    resp = client.patch(f"/api/v1/soa/entries/{entry_id}", json={"is_applicable": False}, headers=headers)
    assert resp.status_code == 422

    resp = client.patch(
        f"/api/v1/soa/entries/{entry_id}",
        json={"is_applicable": False, "justification": "No manejamos ese proceso"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_applicable"] is False
    assert resp.json()["justification"] == "No manejamos ese proceso"


def test_summary_counts(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    client.post("/api/v1/soa/instantiate", headers=headers)
    entries = client.get("/api/v1/soa/entries", headers=headers).json()

    client.patch(
        f"/api/v1/soa/entries/{entries[0]['id']}",
        json={"is_applicable": False, "justification": "no aplica"},
        headers=headers,
    )
    client.patch(
        f"/api/v1/soa/entries/{entries[1]['id']}",
        json={"implementation_status": "implemented"},
        headers=headers,
    )
    client.patch(
        f"/api/v1/soa/entries/{entries[2]['id']}",
        json={"implementation_status": "in_progress"},
        headers=headers,
    )

    resp = client.get("/api/v1/soa/summary", headers=headers)
    summary = resp.json()
    assert summary["total"] == 93
    assert summary["excluded"] == 1
    assert summary["applicable"] == 92
    assert summary["implemented"] == 1
    assert summary["in_progress"] == 1
    assert summary["not_started"] == 91


def test_viewer_cannot_update_entry(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin_headers = auth_headers(tenant["id"])
    client.post("/api/v1/soa/instantiate", headers=admin_headers)
    entry_id = client.get("/api/v1/soa/entries", headers=admin_headers).json()[0]["id"]

    viewer_headers = auth_headers(tenant["id"], role="viewer")
    resp = client.patch(
        f"/api/v1/soa/entries/{entry_id}", json={"notes": "intento"}, headers=viewer_headers
    )
    assert resp.status_code == 403


def test_soa_entries_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    client.post("/api/v1/soa/instantiate", headers=auth_headers(tenant_a["id"]))

    resp = client.get("/api/v1/soa/entries", headers=auth_headers(tenant_b["id"]))
    assert resp.json() == []
