def _control_id(client, headers):
    client.post("/api/v1/soa/instantiate", headers=headers)
    return client.get("/api/v1/soa/entries", headers=headers).json()[0]["control"]["id"]


def test_create_asset_and_risk_computes_inherent_score_and_level(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    resp = client.post(
        "/api/v1/risk/assets",
        json={"name": "Base de datos de clientes", "category": "information"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    asset_id = resp.json()["id"]

    cases = [
        (1, 1, 1, "low"),
        (3, 3, 9, "medium"),
        (3, 5, 15, "high"),
        (5, 5, 25, "critical"),
    ]
    for likelihood, impact, expected_score, expected_level in cases:
        resp = client.post(
            "/api/v1/risk/risks",
            json={
                "asset_id": asset_id,
                "title": f"Riesgo {likelihood}x{impact}",
                "likelihood": likelihood,
                "impact": impact,
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["inherent_score"] == expected_score
        assert body["inherent_level"] == expected_level
        assert body["status"] == "open"
        assert body["asset_id"] == asset_id


def test_update_risk_recomputes_residual_score_and_level(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    control_id = _control_id(client, headers)

    resp = client.post(
        "/api/v1/risk/risks",
        json={"title": "Riesgo de acceso indebido", "likelihood": 5, "impact": 5, "control_ids": [control_id]},
        headers=headers,
    )
    risk = resp.json()
    assert risk["inherent_level"] == "critical"
    assert risk["control_ids"] == [control_id]

    resp = client.patch(
        f"/api/v1/risk/risks/{risk['id']}",
        json={
            "treatment_decision": "mitigate",
            "treatment_plan": "Implementar MFA y cifrado en reposo",
            "residual_likelihood": 1,
            "residual_impact": 2,
            "status": "treating",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["residual_score"] == 2
    assert updated["residual_level"] == "low"
    assert updated["status"] == "treating"
    assert updated["treatment_decision"] == "mitigate"
    # inherent values untouched by the residual update
    assert updated["inherent_score"] == 25
    assert updated["inherent_level"] == "critical"


def test_replacing_control_links_on_risk(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    client.post("/api/v1/soa/instantiate", headers=headers)
    entries = client.get("/api/v1/soa/entries", headers=headers).json()
    control_a, control_b = entries[0]["control"]["id"], entries[1]["control"]["id"]

    resp = client.post(
        "/api/v1/risk/risks",
        json={"title": "Riesgo múltiple", "likelihood": 2, "impact": 2, "control_ids": [control_a]},
        headers=headers,
    )
    risk_id = resp.json()["id"]
    assert resp.json()["control_ids"] == [control_a]

    resp = client.patch(
        f"/api/v1/risk/risks/{risk_id}", json={"control_ids": [control_b]}, headers=headers
    )
    assert resp.json()["control_ids"] == [control_b]

    resp = client.patch(f"/api/v1/risk/risks/{risk_id}", json={"control_ids": []}, headers=headers)
    assert resp.json()["control_ids"] == []


def test_viewer_cannot_write_risk_or_asset(client, make_tenant, auth_headers):
    tenant = make_tenant()
    viewer_headers = auth_headers(tenant["id"], role="viewer")

    resp = client.post(
        "/api/v1/risk/assets", json={"name": "X", "category": "other"}, headers=viewer_headers
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/risk/risks",
        json={"title": "X", "likelihood": 1, "impact": 1},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_assets_and_risks_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    headers_a = auth_headers(tenant_a["id"])
    headers_b = auth_headers(tenant_b["id"])

    client.post("/api/v1/risk/assets", json={"name": "Solo A", "category": "hardware"}, headers=headers_a)
    client.post("/api/v1/risk/risks", json={"title": "Solo A", "likelihood": 2, "impact": 2}, headers=headers_a)

    assert client.get("/api/v1/risk/assets", headers=headers_b).json() == []
    assert client.get("/api/v1/risk/risks", headers=headers_b).json() == []
